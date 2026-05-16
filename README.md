# cryptic

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/camillescott/cryptic/docker-publish.yml)
[![Docker Image Version](https://img.shields.io/docker/v/camillescott/cryptic?logo=docker)](https://hub.docker.com/r/camillescott/cryptic)
[![PyPI - Version](https://img.shields.io/pypi/v/cryptic-md)](https://pypi.org/project/cryptic-md/)
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)

> The Cryptics have a fearful reputation, and yet this one – the first specimen I’ve ever seen – seems . . . ‘Imbecilic?’
> -- _Words of Radiance_


Cryptic runs a persistent service that watches directories for incoming markdown files with some basic frontmatter and a body containing the raw HTML content of a website. The content is shipped off to an LLM provider (OpenAI by default), categorized, and summarized, with different summarizations and metadata extraction depending on the category. It uses [structured output](https://developers.openai.com/api/docs/guides/structured-outputs) for reliability, and the entire prompt (other than the system prompt) is defined in the pydantic models. The results are then written out to finalized Markdown in configured output directories.

It's designed to pair with [Obsidian Headless Sync](https://obsidian.md/help/sync/headless) and [Obsidian Web Clipper](https://obsidian.md/help/web-clipper). Web Clipper can do LLM processing out of the box, but the output formatting is somewhat limiting; an independent service allows much more flexibility in prompt design and output constraints.

I've included a basic webclipper template for reference in this repository.

## Installation

From PyPI:

```sh
pip install cryptic-md
```

From source, clone and run:

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
  vaults:
    personal:
      input_dir: ~/Obsidian/Personal/cryptic-staging
      output_dir: ~/Obsidian/Personal/cryptic-processed
      originals_dir: ~/Obsidian/cryptic-originals
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

## Docker

Pre-built images are published to Docker Hub at `camillescott/cryptic`. The included `compose.yaml` is the simplest way to run the service:

```sh
export OPENAI_API_KEY=sk-...
docker compose up -d
```

It bind-mounts `./vaults` → `/vaults` (your Obsidian tree) and `./config` → `/config` (a directory containing `config.yaml`). Paths inside `config.yaml` must be rooted at `/vaults`, for example `/vaults/personal/cryptic-staging`.

To build the image locally instead of pulling:

```sh
docker build -t cryptic .
```

inotify works across bind mounts on Linux hosts. On Docker Desktop for macOS or Windows, host filesystem events don't propagate into the container.

---

Portions of this project's code have been written with agentic coding tools.
