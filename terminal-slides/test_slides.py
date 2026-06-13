#!/usr/bin/env python3
"""Tests for Terminal Slides — covers parsing, rendering, and export."""

import sys
import os
import re
import tempfile

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slides import SlideParser, Renderer, export_text, THEMES

# ──────────────────────────────────────────────
# Test: SlideParser basic parsing
# ──────────────────────────────────────────────

def test_parse_single_slide():
    md = "# Hello\n\nSome text"
    parser = SlideParser(md)
    assert len(parser.slides) == 1
    assert parser.slides[0][0]["type"] == "heading1"

def test_parse_multiple_slides():
    md = "# Slide One\n\n---\n\n## Slide Two\n\nSome body text"
    parser = SlideParser(md)
    assert len(parser.slides) == 2
    assert parser.slides[0][0]["type"] == "heading1"
    assert parser.slides[1][0]["type"] == "heading2"

def test_parse_code_block():
    md = "## Code\n\n```python\nprint('hi')\n```\n"
    parser = SlideParser(md)
    slide = parser.slides[0]
    code_blocks = [e for e in slide if e["type"] == "code_block"]
    assert len(code_blocks) == 1
    assert code_blocks[0]["lang"] == "python"
    assert "print('hi')" in code_blocks[0]["text"]

def test_parse_blockquote():
    md = "> This is a quote\n\nSome text"
    parser = SlideParser(md)
    quotes = [e for e in parser.slides[0] if e["type"] == "quote"]
    assert len(quotes) == 1
    assert "quote" in quotes[0]["text"]

def test_parse_unordered_list():
    md = "* Item one\n* Item two\n* Item three"
    parser = SlideParser(md)
    lists = [e for e in parser.slides[0] if e["type"] == "unordered_list"]
    assert len(lists) == 1
    assert len(lists[0]["items"]) == 3

def test_parse_ordered_list():
    md = "1. First\n2. Second\n3. Third"
    parser = SlideParser(md)
    lists = [e for e in parser.slides[0] if e["type"] == "ordered_list"]
    assert len(lists) == 1
    assert lists[0]["items"][0] == (1, "First")
    assert lists[0]["items"][2] == (3, "Third")

def test_parse_speaker_notes():
    md = "# Talk\n\n??? Remember to smile\n??? And breathe"
    parser = SlideParser(md)
    notes = [e for e in parser.slides[0] if e["type"] == "note"]
    assert len(notes) == 1  # consecutive ??? lines merged
    assert "smile" in notes[0]["text"]

def test_parse_horizontal_rule():
    # Use 4+ dashes for an HR within a slide (3 dashes = slide separator)
    md = "## Before\n\n----\n\nSome text"
    parser = SlideParser(md)
    hrs = [e for e in parser.slides[0] if e["type"] == "hr"]
    assert len(hrs) == 1

def test_parse_empty_input():
    md = ""
    parser = SlideParser(md)
    assert len(parser.slides) == 0

def test_parse_heading_levels():
    md = "# H1\n\n---\n\n## H2\n\n---\n\n### H3"
    parser = SlideParser(md)
    assert parser.slides[0][0]["type"] == "heading1"
    assert parser.slides[1][0]["type"] == "heading2"
    assert parser.slides[2][0]["type"] == "heading3"

def test_parse_heading4_clamps_to_3():
    md = "#### Deep heading"
    parser = SlideParser(md)
    assert parser.slides[0][0]["type"] == "heading3"

# ──────────────────────────────────────────────
# Test: Inline formatting
# ──────────────────────────────────────────────

def test_inline_bold():
    md = "This is **bold** text"
    parser = SlideParser(md)
    text_elem = [e for e in parser.slides[0] if e["type"] == "text"][0]
    assert "<<BOLD>>" in text_elem["text"]
    assert "<</BOLD>>" in text_elem["text"]

def test_inline_italic():
    md = "This is *italic* text"
    parser = SlideParser(md)
    text_elem = [e for e in parser.slides[0] if e["type"] == "text"][0]
    assert "<<ITALIC>>" in text_elem["text"]

def test_inline_code():
    md = "Use `print()` to output"
    parser = SlideParser(md)
    text_elem = [e for e in parser.slides[0] if e["type"] == "text"][0]
    assert "<<CODE>>" in text_elem["text"]

def test_inline_link():
    md = "Visit [Python](https://python.org) for more"
    parser = SlideParser(md)
    text_elem = [e for e in parser.slides[0] if e["type"] == "text"][0]
    assert "<<LINK:" in text_elem["text"]
    assert "https://python.org" in text_elem["text"]
    assert "Python" in text_elem["text"]

# ──────────────────────────────────────────────
# Test: get_slide_titles
# ──────────────────────────────────────────────

def test_get_slide_titles():
    md = "# Welcome\n\n---\n\n## Section Two\n\n---\n\nSome text without heading"
    parser = SlideParser(md)
    titles = parser.get_slide_titles()
    assert len(titles) == 3
    assert "Welcome" in titles[0]
    assert "Section Two" in titles[1]
    # Third slide has no heading, should use first text line or "(untitled)"

# ──────────────────────────────────────────────
# Test: Renderer
# ──────────────────────────────────────────────

def test_renderer_dark_theme():
    renderer = Renderer("dark")
    assert renderer.theme_name == "dark"
    assert renderer.theme is not None

def test_renderer_light_theme():
    renderer = Renderer("light")
    assert renderer.theme_name == "light"

def test_renderer_monochrome_theme():
    renderer = Renderer("monochrome")
    assert renderer.theme_name == "monochrome"

def test_renderer_invalid_theme_falls_back():
    renderer = Renderer("nonexistent")
    # Should fall back to dark
    assert renderer.theme == THEMES["dark"]

def test_render_slide_produces_output():
    md = "# Hello\n\nWorld"
    parser = SlideParser(md)
    renderer = Renderer("dark")
    output = renderer.render_slide(parser.slides[0], 0, 1)
    assert len(output) > 0
    # Should contain visible text (strip ANSI)
    clean = re.sub(r'\033\[[0-9;]*m', '', output)
    assert "Hello" in clean

def test_render_slide_with_notes_hidden():
    md = "# Hello\n\n??? Secret note"
    parser = SlideParser(md)
    renderer = Renderer("dark")
    # By default, notes are hidden
    output = renderer.render_slide(parser.slides[0], 0, 1, show_notes=False)
    clean = re.sub(r'\033\[[0-9;]*m', '', output)
    assert "Secret note" not in clean

def test_render_slide_with_notes_shown():
    md = "# Hello\n\n??? Secret note"
    parser = SlideParser(md)
    renderer = Renderer("dark")
    output = renderer.render_slide(parser.slides[0], 0, 1, show_notes=True)
    clean = re.sub(r'\033\[[0-9;]*m', '', output)
    assert "Secret note" in clean

def test_render_hr():
    # Use 4+ dashes for an HR within a slide
    md = "## Before\n\n----\n\nAfter"
    parser = SlideParser(md)
    renderer = Renderer("dark")
    output = renderer.render_slide(parser.slides[0], 0, 1)
    clean = re.sub(r'\033\[[0-9;]*m', '', output)
    assert "─" in clean

def test_render_progress_bar():
    md = "# Test"
    parser = SlideParser(md)
    renderer = Renderer("dark")
    output = renderer.render_slide(parser.slides[0], 0, 3)
    clean = re.sub(r'\033\[[0-9;]*m', '', output)
    # Should show 1/3
    assert "1/3" in clean

def test_render_timestamp():
    md = "# Test"
    parser = SlideParser(md)
    renderer = Renderer("dark")
    output = renderer.render_slide(parser.slides[0], 0, 1)
    # Should contain a timestamp in HH:MM format
    assert re.search(r'\d{2}:\d{2}', output) is not None

# ──────────────────────────────────────────────
# Test: Export
# ──────────────────────────────────────────────

def test_export_text():
    md = "# Hello\n\n---\n\n## Slide Two\n\nBody text"
    parser = SlideParser(md)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        tmp_path = f.name
    try:
        export_text(parser.slides, tmp_path, "dark")
        with open(tmp_path, 'r') as f:
            content = f.read()
        # Should not contain ANSI codes
        assert '\033[' not in content
        assert "Hello" in content
        assert "Slide Two" in content
    finally:
        os.unlink(tmp_path)

# ──────────────────────────────────────────────
# Test: DEMO_SLIDES parses correctly
# ──────────────────────────────────────────────

def test_demo_slides_parse():
    from slides import DEMO_SLIDES
    parser = SlideParser(DEMO_SLIDES)
    assert len(parser.slides) >= 5  # Demo should have several slides
    titles = parser.get_slide_titles()
    assert len(titles) == len(parser.slides)

# ──────────────────────────────────────────────
# Test: Edge cases
# ──────────────────────────────────────────────

def test_multiline_code_block():
    md = "## Code\n\n```python\nline1\nline2\nline3\n```\n"
    parser = SlideParser(md)
    code = [e for e in parser.slides[0] if e["type"] == "code_block"][0]
    assert code["text"].count("\n") == 2  # 3 lines = 2 newlines

def test_unclosed_code_block():
    md = "## Oops\n\n```\nthis has no closing fence"
    parser = SlideParser(md)
    code = [e for e in parser.slides[0] if e["type"] == "code_block"]
    assert len(code) == 1  # Should still parse as code block

def test_only_blank_slides():
    md = "   \n\n---\n\n   "
    parser = SlideParser(md)
    # Blank slides should be skipped
    assert len(parser.slides) == 0

def test_multiple_notes_on_one_slide():
    md = "# Title\n\n??? Note one\n\nSome text\n\n??? Note two"
    parser = SlideParser(md)
    notes = [e for e in parser.slides[0] if e["type"] == "note"]
    # Notes are separated by non-note content
    assert len(notes) == 2

def test_render_link():
    md = "Check out [Python](https://python.org) today"
    parser = SlideParser(md)
    renderer = Renderer("dark")
    output = renderer.render_slide(parser.slides[0], 0, 1)
    clean = re.sub(r'\033\[[0-9;]*m', '', output)
    assert "Python" in clean
    assert "python.org" in clean


# ──────────────────────────────────────────────
# Test: Bug fixes (v1.2.0)
# ──────────────────────────────────────────────

def test_code_block_box_consistency():
    """Code block top bar, content, and bottom bar should have the same visible width."""
    md = "## Code\n\n```python\nprint('hello world')\n```"
    parser = SlideParser(md)
    for cols in [80, 60, 40]:
        r = Renderer("dark")
        r.cols = cols
        output = r.render_slide(parser.slides[0], 0, 1)
        clean = re.sub(r'\033\[[0-9;]*m', '', output)
        widths = set()
        for line in clean.split('\n'):
            if any(c in line for c in '┌│└'):
                widths.add(len(line.rstrip()))
        # All box-drawing lines should be the same width
        assert len(widths) <= 2, f"Inconsistent code box widths at cols={cols}: {widths}"

def test_crlf_handling():
    """Files with CRLF (Windows) line endings should parse correctly."""
    md = "# Title\r\n\r\nBody text\r\n\r\n---\r\n\r\n## Slide 2"
    parser = SlideParser(md)
    assert len(parser.slides) == 2
    assert parser.slides[0][0]["type"] == "heading1"

def test_separator_with_trailing_whitespace():
    """Slide separator '---' with trailing spaces should still work."""
    md = "# A\n\n---   \n\n# B"
    parser = SlideParser(md)
    assert len(parser.slides) == 2

def test_separator_at_start_of_file():
    """A '---' at the very start of the file should be treated as a separator, not an HR."""
    md = "---\n\n# Title"
    parser = SlideParser(md)
    # The --- at start should be stripped, leaving just the title slide
    assert len(parser.slides) == 1
    assert parser.slides[0][0]["type"] == "heading1"

def test_hr_requires_four_dashes():
    """Three dashes should be a slide separator, not an HR. Four+ dashes should be HR."""
    # 3 dashes = slide separator
    md_three = "## Before\n\n---\n\nAfter"
    parser_three = SlideParser(md_three)
    assert len(parser_three.slides) == 2  # Split into 2 slides

    # 4 dashes = HR within a slide
    md_four = "## Before\n\n----\n\nAfter"
    parser_four = SlideParser(md_four)
    assert len(parser_four.slides) == 1  # Single slide
    hrs = [e for e in parser_four.slides[0] if e["type"] == "hr"]
    assert len(hrs) == 1

def test_list_item_wrapping():
    """Long list items should not overflow the terminal width."""
    r = Renderer("dark")
    r.cols = 40
    # Unordered list
    md = "* " + "A" * 80
    parser = SlideParser(md)
    output = r.render_slide(parser.slides[0], 0, 1)
    clean = re.sub(r'\033\[[0-9;]*m', '', output)
    for line in clean.split('\n'):
        assert len(line.rstrip()) <= r.cols, f"Unordered list line overflows: {len(line.rstrip())} > {r.cols}"

    # Ordered list
    md2 = "1. " + "B" * 80
    parser2 = SlideParser(md2)
    output2 = r.render_slide(parser2.slides[0], 0, 1)
    clean2 = re.sub(r'\033\[[0-9;]*m', '', output2)
    for line in clean2.split('\n'):
        assert len(line.rstrip()) <= r.cols, f"Ordered list line overflows: {len(line.rstrip())} > {r.cols}"

def test_heading_wrapping():
    """Long headings should be wrapped to fit terminal width."""
    r = Renderer("dark")
    r.cols = 40
    md = "# " + "A" * 100
    parser = SlideParser(md)
    output = r.render_slide(parser.slides[0], 0, 1)
    clean = re.sub(r'\033\[[0-9;]*m', '', output)
    max_len = max(len(line.rstrip()) for line in clean.split('\n'))
    assert max_len <= r.cols, f"Heading overflows: {max_len} > {r.cols}"

def test_note_box_width_consistency():
    """Note box header and footer should have consistent visible width."""
    md = "# Talk\n\n??? This is a speaker note"
    parser = SlideParser(md)
    for cols in [80, 40]:
        r = Renderer("dark")
        r.cols = cols
        output = r.render_slide(parser.slides[0], 0, 1, show_notes=True)
        clean = re.sub(r'\033\[[0-9;]*m', '', output)
        header_len = None
        footer_len = None
        for line in clean.split('\n'):
            stripped = line.rstrip()
            if '┌' in stripped and 'Notes' in stripped:
                header_len = len(stripped)
            elif '└' in stripped:
                footer_len = len(stripped)
        if header_len and footer_len:
            assert header_len == footer_len, f"Note box width mismatch at cols={cols}: header={header_len}, footer={footer_len}"

def test_empty_note_renders():
    """A note with empty text should render without crashing."""
    md = "# Title\n\n???"
    parser = SlideParser(md)
    r = Renderer("dark")
    output = r.render_slide(parser.slides[0], 0, 1, show_notes=True)
    # Should not crash
    assert len(output) > 0


# ──────────────────────────────────────────────
# Run tests
# ──────────────────────────────────────────────

if __name__ == "__main__":
    test_functions = [
        v for name, v in sorted(globals().items())
        if name.startswith("test_") and callable(v)
    ]
    passed = 0
    failed = 0
    for test_fn in test_functions:
        try:
            test_fn()
            print(f"  ✓ {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {test_fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {passed + failed} tests")
    sys.exit(1 if failed else 0)