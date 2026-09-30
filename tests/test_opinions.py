from opinions import parse_opinions


def test_parse_opinions_extracts_content_after_heading():
    page_html = """
        <html>
          <head><style>.ignored { color: red; }</style></head>
          <body>
            <div>Navigation before heading</div>
            <h1>Correct Opinions</h1>
            <p>Water should not taste like anything or be fizzy</p>
            <p>Movies are always better with subtitles</p>
            <div>Report abuse</div>
            <script>const ignored = "not an opinion";</script>
          </body>
        </html>
    """

    assert parse_opinions(page_html) == {
        1: "Water should not taste like anything or be fizzy",
        2: "Movies are always better with subtitles",
    }


def test_parse_opinions_decodes_html_entities():
    page_html = """
        <h1>Correct Opinions</h1>
        <p>Mac &amp; cheese is a complete meal</p>
    """

    assert parse_opinions(page_html) == {1: "Mac & cheese is a complete meal"}


def test_parse_opinions_returns_empty_dict_without_heading():
    assert parse_opinions("<p>Water should not be fizzy</p>") == {}
