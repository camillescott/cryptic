# cryptic

LLM tools for summarizing web content into structured Obsidian notes.

## Features

- Structured-output summarization via OpenAI, with per-category schemas (papers, articles, events, products, discussions, media, software, references).
- Two-pane note generation: YAML frontmatter for metadata, Markdown body for content. Section layout and frontmatter mapping are declared via Pydantic field annotations.
- Long-running service that watches a directory for new notes, processes them concurrently, and moves results to an output directory. Unmodified copies of each input are archived to a separate directory.
- Persistent retry bookkeeping via a `cryptic_tries` frontmatter field, capped at a configurable `max_tries`.
- Settle delay before reading new files so sources that write incrementally are picked up only once.
- YAML configuration for model list, default model, reasoning effort, prompt text, and service directories.

## Installation

```sh
poetry install
```

Set `OPENAI_API_KEY` in the environment or in a `.env` file in the project root.

## Configuration

Create `~/.config/cryptic/config.yaml`:

```yaml
openai:
  models:
    - gpt-5.4-mini
  default_model: gpt-5.4-mini
  default_reasoning: medium

service:
  input_dir: ~/Obsidian/Personal/cryptic-staging
  output_dir: ~/Obsidian/Personal/cryptic-processed
  originals_dir: ~/Obsidian/Personal/cryptic-originals
  max_concurrent: 3
  max_tries: 3
  pickup_delay_seconds: 3.0
```

Override the config path per-invocation with `--config /path/to/config.yaml`.

## Usage

Process a single note in place:

```sh
cryptic process note --note path/to/note.md
```

Run the service against the configured directories:

```sh
cryptic service
```

Drain the input directory once and exit (useful for batch runs):

```sh
cryptic service --once
```

Common flags available on both commands:

- `--model NAME` — pick a model from `openai.models`.
- `--reasoning {low,medium,high,xhigh}` — set reasoning effort.
- `--config PATH` — use an alternate config file.

---

Portions of this project's code have been written with agentic coding tools.
