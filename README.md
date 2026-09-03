# TheWayToLearn

**English** · [繁體中文](docs/README.zh-TW.md)

Turn a list of YouTube links into a structured learning plan: transcript, key-moment screenshots, step-by-step reasoning, inline term explanations, and a map that links every video you have processed.

Built as a set of [Claude Code](https://claude.com/claude-code) skills plus the deterministic scripts those skills call.

---

## Why this exists

Watching a technical video leaves you with a vague feeling of "I get it" and nothing you can revisit. Notes taken by hand skip the reasoning. Auto-summaries flatten the argument into bullet points and lose the order in which ideas were introduced.

This project keeps the order. Each segment of the video is explained **linearly**: the clue left by segment N is the starting point of segment N+1, terms are defined the first time they appear, and forward references are forbidden. The result reads like the video argued it, not like a table of contents.

## What you get

For each video, a folder under `workspace/<video title>/` containing a self-contained `plan.html` with a fixed five-part structure:

1. **Background & outline** – what you need to know before watching, and the video's outline
2. **The author's line of reasoning** – how the conclusion is built step by step
3. **Segment-by-segment walkthrough** – for every segment: summary with timestamps and screenshots, an AI supplement, terms explained in place (hover for translation, click for a longer note), and any **errata / outdated claims** backed by verbatim transcript quotes
4. **Summary**
5. **Three next steps** – three directions, each with suggested YouTube search keywords

Every `plan.html` embeds three Mermaid diagrams: a reasoning-chain flowchart, a mind map (topic → segments → terms), and a term-relationship graph.

Once you have two or more videos, `workspace/atlas.html` is a **learning atlas**: each video is a waypoint, routes between them are typed (prerequisite / deepens / contrasts / applies / related), and waypoints are grouped into topic regions. Each plan links back to the atlas and to its neighbours.

Intermediate results (`transcript.json`, `segments.json`, `frames/`, `analysis.json`, `timings.json`) are files on disk, so any stage can be rerun without refetching the video.

## How to use it

### Inside Claude Code (the intended way)

Open this repository in Claude Code and paste links:

```
/learn https://www.youtube.com/watch?v=XXXXXXXXXXX https://youtu.be/YYYYYYYYYYY
/learn input.yaml
```

Step 0 always prints a cost estimate (time, tokens, disk) per stage and in total, then waits for your go-ahead. Then for each video it runs fetch → segment → shot → analyze → render, and updates the atlas when there are two or more videos.

Options:

```
/learn <url> --vision true|false|auto   # whether the agent reads every screenshot (default true); applies to the preceding URL
/learn --from <stage> <video_id>        # rerun from fetch | segment | shot | analyze | render
/learn --dry-run <url> ...              # list what would run or be skipped
```

Each stage is also its own skill (`/learn-estimate`, `/learn-fetch`, `/learn-segment`, `/learn-shot`, `/learn-analyze`, `/learn-render`, `/learn-atlas`) with the convention `/learn-<stage> <video_id> [--force]`. Existing outputs are never overwritten unless you pass `--force`.

Batch input (`input.example.yaml`):

```yaml
lang: [zh-TW, zh, en]   # subtitle language preference
out: workspace
videos:
  - url: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    vision: true         # true | false | auto
  - url: https://youtu.be/xxxxxxxxxxx
    vision: false
```

### Running the scripts directly

The deterministic stages are plain Python and work without an agent:

| Command | What it does |
|---|---|
| `uv run scripts/estimate.py <url> ...` | Estimate time / tokens / disk per stage. No download. |
| `uv run scripts/fetch.py <url>` | Fetch subtitles (with timestamps) and metadata. No video download. |
| `uv run scripts/screenshot.py <id>` | Download the video once, extract frames listed in `segments.json` with ffmpeg, delete the video (`--keep-video` to keep it). |
| `uv run scripts/validate.py <segments\|analysis\|overview> <file.json>` | Validate agent-written JSON against the schemas and the linear-progression rules. |
| `uv run scripts/render.py [ids...]` | Render `plan.html` per video. `--combined` merges several into one file. |
| `uv run scripts/atlas.py --status` / `uv run scripts/atlas.py` | List new waypoints and shared terms / validate `atlas.json` and render `atlas.html`. |

The segment, analyze, and overview stages need an LLM and are performed by the agent following `rules/*.md`.

## Requirements

| Dependency | Why | How it is installed |
|---|---|---|
| Python ≥ 3.11 | scripts | see below |
| [uv](https://docs.astral.sh/uv/) | dependency and venv management | see below |
| yt-dlp | subtitles, metadata, video download | Python package, pulled in by `uv sync` |
| ffmpeg | frame extraction | **system package, install separately** |
| Claude Code | runs the `/learn-*` skills | [install guide](https://docs.claude.com/en/docs/claude-code) |

Python packages (`pyproject.toml`): `yt-dlp`, `pyyaml`, `jinja2`, `jsonschema`; dev: `pytest`, `ruff`.

## Setting up your machine

Developed and tested on WSL2 (Ubuntu). Native macOS and Windows should work; the only OS-specific piece is getting `ffmpeg` onto your `PATH`.

### Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # uv (installs Python if needed)
sudo apt install ffmpeg                             # Debian / Ubuntu
# sudo dnf install ffmpeg                           # Fedora (RPM Fusion enabled)
git clone <this repo> && cd TheWayToLearn
uv sync
```

### macOS

```bash
brew install uv ffmpeg
git clone <this repo> && cd TheWayToLearn
uv sync
```

### Windows

Option A – WSL2 (recommended, matches the tested setup): install Ubuntu from the Microsoft Store, then follow the Linux steps inside it.

Option B – native PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
winget install Gyan.FFmpeg        # or: choco install ffmpeg
# open a new terminal so PATH is refreshed
git clone <this repo>; cd TheWayToLearn
uv sync
```

### Verify

```bash
uv run yt-dlp --version
ffmpeg -version
uv run pytest -q          # offline; uses tests/fixtures/ws as a sample workspace
uv run scripts/estimate.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

If the last command prints a per-stage table, you are ready.

## Changing behaviour without touching code

| To change… | Edit |
|---|---|
| segmentation, screenshot picking, `vision: auto` decision | `rules/segment.md` |
| linear-progression rules and explanation style | `rules/narrative.md` (hard rules are enforced by `scripts/validate.py`; add a check and a test when you add one) |
| summary, takeaways, the three next steps | `rules/overview.md` |
| how routes and regions are decided in the atlas | `rules/atlas.md` |
| page layout | `rules/output.md` + `templates/plan.html.j2` |
| estimate coefficients | `config/estimate.yaml` |
| agent output format | `schemas/*.json` |

## Development

```bash
uv run pytest -q                         # all tests, no network
uv run pytest tests/test_validate.py -k forward
uv run ruff check scripts tests
```

## Translations

This README is the English source. Other languages live in `docs/README.<lang>.md` using [BCP 47](https://en.wikipedia.org/wiki/IETF_language_tag) tags, and every version carries the same language row at the top.

To add a language: copy `README.md` to `docs/README.<lang>.md`, translate, then add the link to the language row in **every** README (including this one).

| Language | File |
|---|---|
| English (source) | `README.md` |
| 繁體中文 | `docs/README.zh-TW.md` |
