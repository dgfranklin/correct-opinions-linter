# Correct Opinions Linter 🚨

A Discord bot that lints server messages and calls out anyone who violates the [Correct Opinions](https://www.correctopinions.info/).

Uses **TypeSafe Jev** by default to determine if a message contradicts any of the correct
opinions. Google Gemini remains available as an alternative evaluator. Opinions are **fetched
live** from the website at startup and refreshed automatically every hour, so the bot always
stays in sync.

## Example

> **User:** I love sparkling water, it's so refreshing!
>
> **Bot:** 🚨 **Correct Opinion Violation Detected!** 🚨
>
> • **#2**: *"Water should not taste like anything or be fizzy"*
>
> Please correct your opinions accordingly.

## Prerequisites

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → give it a name → click **Create**
3. Go to the **Bot** tab → click **Reset Token** → copy the token
4. Under **Privileged Gateway Intents**, enable **Message Content Intent**
5. Go to the **OAuth2** tab → **URL Generator**:
   - Check **bot** under Scopes
   - Check **Send Messages** and **Read Message History** under Bot Permissions
6. Copy the generated URL and open it in your browser to invite the bot to your server

### 2. Get a TypeSafe API key

Create a key in the [TypeSafe Console](https://console.typesafe.ai/) and set it as
`TYPESAFE_API_KEY` or `JEV_API_KEY`.

### Optional: Get a Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Copy the key

## Running with Docker (Recommended)

```bash
# Build the image
docker build -t correct-opinions-bot .

# Run the container
docker run -d \
  -e DISCORD_BOT_TOKEN="your-discord-bot-token" \
  -e TYPESAFE_API_KEY="your-typesafe-api-key" \
  -e OPINION_EVALUATOR="jev" \
  --name opinions-bot \
  --restart unless-stopped \
  correct-opinions-bot
```

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | *(required)* | Your Discord bot token |
| `OPINION_EVALUATOR` | `jev` | Evaluator provider: `jev` or `gemini` |
| `TYPESAFE_API_KEY` / `JEV_API_KEY` | *(required for Jev)* | Your TypeSafe API key |
| `GEMINI_API_KEY` | *(required for Gemini)* | Your Google Gemini API key |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Gemini model used to lint messages |
| `JEV_MODEL` | `jev-latest` | TypeSafe model or alias used to lint messages |
| `JEV_THRESHOLD` | `0.5` | Minimum Noul probability treated as a violation |
| `OPINIONS_REFRESH_INTERVAL` | `3600` | How often (in seconds) to re-fetch opinions from the website |

### Managing the Container

```bash
# View logs
docker logs -f opinions-bot

# Stop the bot
docker stop opinions-bot

# Restart the bot
docker restart opinions-bot

# Remove the container
docker rm -f opinions-bot
```

## Running without Docker

```bash
# Create an isolated environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# Configure the bot, then fill in your real tokens
cp .env.example .env
set -a; source .env; set +a

# Run the bot
python src/discord_bot.py
```

## Development

The development dependencies add Ruff for linting and pytest for tests:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

ruff check .
pytest
```

The test suite and linter do not require API credentials. GitHub Actions runs both on every
pull request and push to `main`.

### Project layout

- `src/discord_bot.py` is the Discord entry point.
- `src/evaluators/` contains the common evaluator contract, provider factory, and model-specific
  implementations.
- `src/opinions.py` fetches and parses the canonical opinion list.
- `src/eval_runner.py` is the model-evaluation CLI; datasets and recorded reports live in
  `evals/`.
- `tests/` contains credential-free unit tests.

### Model evaluations

Opinion classification is separate from the Discord transport. Evaluators implement the
`OpinionEvaluator` interface. `JevOpinionEvaluator` and `GeminiOpinionEvaluator` can be swapped
without changing Discord message handling. Jev evaluates all opinions as parallel TypeSafe
Noul questions in one request and thresholds the returned probabilities in code.

The repository includes a balanced dataset with 38 labeled synthetic and observed messages and
a snapshot of the 40 opinions used to label them. Run it against the configured model with:

```bash
set -a; source .env.local; set +a
python src/eval_runner.py --provider jev
python src/eval_runner.py --provider gemini
```

The runner reports coverage, accuracy over completed cases, overall success rate, precision,
recall, F1, opinion-identification accuracy, a confusion matrix, provider-reported token usage,
and measured request latency. Requests are sequential with a 4.1-second delay by default to
stay within a 15-request-per-minute limit, and each case has a 30-second timeout. Use `--delay 0`
for an account with sufficient quota, `--case sparkling-water` or `--limit 5` for quota-conscious
runs, `--timeout 60` for a slower model, or `--output evals/results/latest.json` to save per-case
details.

## How It Works

1. On startup, the bot fetches the current list of correct opinions from [correctopinions.info](https://www.correctopinions.info/)
2. A background task re-fetches the opinions every hour (configurable) to pick up any changes
3. Every message in all channels the bot can see is sent to the configured evaluator
4. Jev or Gemini determines if the message contradicts any opinion
5. If a violation is found, the bot replies to the message with the violated opinion(s)

## Provider selection

Set `OPINION_EVALUATOR=jev` for TypeSafe Jev or `OPINION_EVALUATOR=gemini` for Google Gemini.
Only the selected provider's API key is required. Provider limits vary by account, so use the
evaluation runner's `--delay` option when benchmarking under a request-per-minute limit.
