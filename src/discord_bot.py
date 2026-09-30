"""
Correct Opinions Linter

Listens to every message in a Discord server and uses the configured model
evaluator to determine if the message violates any of the "correct opinions"
fetched live from https://www.correctopinions.info/

When a violation is detected, the bot replies indicating which opinion was violated.
"""

import asyncio
import logging
import os

import discord

from evaluators import OpinionEvaluator, create_evaluator
from opinions import OpinionStore

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
TYPESAFE_API_KEY = os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY")
JEV_MODEL = os.environ.get("JEV_MODEL", "jev-latest")
JEV_THRESHOLD = float(os.environ.get("JEV_THRESHOLD", "0.5"))
OPINION_EVALUATOR = os.environ.get("OPINION_EVALUATOR", "jev")

# How often (in seconds) to re-fetch opinions from the website (default: 1 hour)
OPINIONS_REFRESH_INTERVAL = int(os.environ.get("OPINIONS_REFRESH_INTERVAL", "3600"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("correct-opinions-bot")

opinion_store = OpinionStore()
evaluator: OpinionEvaluator | None = None


def _get_evaluator() -> OpinionEvaluator:
    """Create the configured evaluator on first use."""
    global evaluator

    if evaluator is None:
        evaluator = create_evaluator(
            OPINION_EVALUATOR,
            gemini_api_key=GEMINI_API_KEY,
            gemini_model=GEMINI_MODEL,
            jev_api_key=TYPESAFE_API_KEY,
            jev_model=JEV_MODEL,
            jev_threshold=JEV_THRESHOLD,
        )

    return evaluator

# ---------------------------------------------------------------------------
# Discord bot
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True  # Required to read message text

client = discord.Client(intents=intents)


async def _periodic_refresh():
    """Background task that re-fetches opinions on a schedule."""
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.sleep(OPINIONS_REFRESH_INTERVAL)
        await opinion_store.refresh()


@client.event
async def on_ready():
    log.info("Bot is online as %s (ID: %s)", client.user, client.user.id)
    opinions = await opinion_store.get_snapshot()
    log.info("Monitoring %d correct opinions", len(opinions))


@client.event
async def on_message(message: discord.Message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Ignore messages from other bots
    if message.author.bot:
        return

    # Ignore empty messages (e.g., image-only)
    if not message.content:
        return

    # Ignore channels that are for games, not opinions
    channel_name = getattr(message.channel, "name", "") or ""
    if "wordle-and-other-games" in channel_name:
        return

    opinions = await opinion_store.get_snapshot()
    if not opinions:
        return

    log.info(
        "Checking message from %s in #%s: %s",
        message.author,
        getattr(message.channel, "name", "DM"),
        message.content[:100],
    )

    try:
        result = await _get_evaluator().evaluate(message.content, opinions)
    except Exception as error:
        log.error("Opinion evaluation failed: %s", error)
        return

    if result.violation:
        opinion_numbers = result.opinion_ids
        violated = []
        for num in opinion_numbers:
            if num in opinions:
                violated.append(f"**#{num}**: *\"{opinions[num]}\"*")

        if violated:
            violations_str = "\n".join(f"• {v}" for v in violated)
            reply = (
                f"🚨 **Correct Opinion Violation Detected!** 🚨\n\n"
                f"{violations_str}\n\n"
                f"Please correct your opinions accordingly."
            )
            log.info("Violation detected for %s: %s", message.author, opinion_numbers)
            await message.reply(reply)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError(
            "Missing DISCORD_BOT_TOKEN environment variable. "
            "Create a bot at https://discord.com/developers/applications and set the token."
        )

    active_evaluator = _get_evaluator()
    log.info("Using opinion evaluator %s", active_evaluator.name)

    # Fetch opinions before starting the bot so we fail fast if the site is down
    await opinion_store.refresh()

    async with client:
        client.loop.create_task(_periodic_refresh())
        await client.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
