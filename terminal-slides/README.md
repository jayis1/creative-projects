# Terminal Slides 🎤🖥️

A presentation tool that runs entirely in your terminal. Write your slides in Markdown, present them with beautiful ANSI colors and keyboard navigation — no GUI required.

## Features

- **Markdown-based slides** — Separate slides with `---`, use standard Markdown syntax
- **Rich inline formatting** — Bold, italic, inline code, and Markdown links `[text](url)`
- **Code blocks** — Language-labeled with box-drawing borders, properly sized to terminal width
- **Blockquotes** — Styled with a sidebar indicator
- **Ordered & unordered lists** — Numbered and bulleted, with long-item wrapping
- **Horizontal rules** — Use `----` (4+ dashes) for decorative separators within a slide
- **Speaker notes** — Lines starting with `???` are hidden by default; press `n` to toggle
- **3 built-in themes** — Dark, Light, and Monochrome
- **Interactive navigation** — Arrow keys, vim keys (j/k/h), Space, Enter, Page Up/Down
- **Jump to slide** — Type a number then Enter to jump directly to that slide
- **First/Last slide** — Press `g` for first, `G` for last
- **Auto-play mode** — Timed slide advancement for unattended presentations
- **Progress bar** — Visual slide progress with timestamp
- **Slide listing** — Use `--list` to print all slide titles
- **Alternate screen buffer** — Your terminal history is preserved after exiting
- **Export to text** — Dump slides to plain text (strips ANSI codes)
- **TTY detection** — Helpful error message if not run in an interactive terminal
- **CRLF support** — Handles Windows-style line endings gracefully
- **Zero dependencies** — Pure Python 3.6+, no external packages needed
- **SSH-friendly** — Present remotely over any terminal connection

## Installation

No installation needed beyond Python 3.6+:

```bash
# Just download and run
chmod +x slides.py
./slides.py demo
```

Or clone this repo:

```bash
git clone <repo-url>
cd terminal-slides
python3 slides.py demo
```

## How to Run

### Built-in Demo

```bash
python3 slides.py --demo
```

### Your Own Presentation

```bash
python3 slides.py presentation.md
```

### With a Specific Theme

```bash
python3 slides.py presentation.md --theme light
python3 slides.py presentation.md --theme monochrome
```

### Auto-play Mode

Advance slides automatically every 5 seconds:

```bash
python3 slides.py presentation.md --auto 5
```

### Export to Plain Text

```bash
python3 slides.py presentation.md --export output.txt
```

### List Slide Titles

```bash
python3 slides.py presentation.md --list
```

### Show Version

```bash
python3 slides.py --version
```

## Usage Examples

### Writing Slides

Create a Markdown file with slides separated by `---`:

```markdown
# My Presentation

A subtitle goes here

---

## Slide Two

* Point one
* Point two
* **Bold text** and *italic text*

---

## Code Example

```python
def hello():
    print("Hello, World!")
```

> A wise quote goes here

---

## Links

Learn more at [Python.org](https://python.org)

---

# Thank You!

Questions?
```

### Speaker Notes

Add hidden speaker notes with `???`:

```markdown
## Key Metrics

Revenue grew 40% YoY

??? remember to mention the Q3 spike was due to the holiday campaign
??? The Q4 forecast is conservative
```

Press `n` during the presentation to toggle note visibility.

### Horizontal Rules Within a Slide

Use `----` (4+ dashes) for a decorative separator within a slide:

```markdown
## Before the break

Important point

----

After the break

Another point
```

> **Note:** Three dashes `---` on a line by themselves separate slides. Use four or more dashes for a visual rule within a slide.

### Supported Markdown Syntax

| Syntax | Result |
|--------|--------|
| `# Heading` | Centered title slide |
| `## Heading` | Section heading |
| `### Heading` | Sub-section heading |
| `**bold**` | Bold colored text |
| `*italic*` | Italic colored text |
| `` `code` `` | Inline code highlight |
| ` ```lang ` code blocks | Boxed code with language label |
| `> quote` | Blockquote with side bar |
| `- item` | Unordered list |
| `1. item` | Ordered list |
| `[text](url)` | Link with URL shown inline |
| `??? note` | Speaker note (hidden by default) |
| `----` | Horizontal rule within a slide |
| `---` | Slide separator |

### Keyboard Controls

| Key | Action |
|-----|--------|
| `→` / `Space` / `Enter` / `j` | Next slide |
| `←` / `h` | Previous slide |
| `g` | First slide |
| `G` | Last slide |
| `n` | Toggle speaker notes |
| `1`–`9` then `Enter` | Jump to slide number |
| `r` | Refresh (re-read terminal size) |
| `q` / `Ctrl+C` | Quit |

## How It Works

1. **Parsing**: The `SlideParser` reads Markdown text, splits on `---` separators, and converts each slide into a list of semantic elements (headings, lists, code blocks, notes, etc.)

2. **Theming**: Three built-in color themes map each element type (title, body, code, quote, note, etc.) to ANSI color + style combinations

3. **Rendering**: The `Renderer` converts each slide's element list into ANSI-decorated strings, centering title slides, drawing box-drawing characters around code blocks, and wrapping long text to fit the terminal

4. **Presentation**: The `Presenter` uses the alternate screen buffer and raw terminal input to create an interactive slide-show experience without any curses dependency

5. **Speaker Notes**: Notes marked with `???` are parsed but hidden by default; pressing `n` toggles their visibility so you can reference them during a talk

## Testing

Run the built-in test suite:

```bash
python3 test_slides.py
```

The tests cover parsing, inline formatting, rendering, export, speaker notes, horizontal rules, CRLF handling, code block sizing, list wrapping, heading wrapping, note box consistency, and edge cases — all without requiring an interactive terminal.

## Changelog

### v1.2.0 — Bug Fix Release

- **Fixed**: Code block box borders and content lines now have consistent widths (were off by 1)
- **Fixed**: Note box header and footer now have matching widths
- **Fixed**: Long unordered and ordered list items now wrap to fit the terminal width
- **Fixed**: Long headings (h1, h2, h3) now wrap to fit the terminal width
- **Fixed**: CRLF (Windows) line endings are now handled gracefully — `\r` characters no longer appear in parsed text
- **Fixed**: Slide separators now accept trailing whitespace (e.g., `--- ` instead of requiring exact `---`)
- **Fixed**: `---` at the very start of a file is now treated as a separator, not parsed as an HR element
- **Fixed**: Horizontal rules now require 4+ dashes (`----`) instead of 3+ — this eliminates the conflict with the `---` slide separator
- **Fixed**: `_wrap_text()` now properly measures visible text width by stripping both ANSI codes and inline format markers
- **Fixed**: Quote wrapping now strips inline format markers for accurate width measurement
- **Fixed**: Note content wrapping now strips inline format markers for accurate width measurement
- **Fixed**: Empty notes (just `???` with no text) no longer crash — they render an empty note box
- **Added**: 9 new tests covering all fixed bugs

### v1.1.0 — Feature Release

- Added speaker notes, markdown links, slide goto, --list, --version, timestamp, horizontal rules, refresh key, TTY detection, Page Up/Down support
- Added 33 unit tests

### v1.0.0 — Initial Release

- Basic terminal-based Markdown presentation tool

## File Structure

```
terminal-slides/
├── slides.py       # The complete presentation tool (single file)
├── sample.md       # Example presentation with notes and links
├── test_slides.py  # Test suite (42 tests)
└── README.md       # This file
```

## License

MIT