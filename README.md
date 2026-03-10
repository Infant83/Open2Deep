# Open2Deep

Open2Deep is an on-prem CLI agent built on top of `deepagents`. It is designed
to run from any project directory, load layered local context, and combine
prompt memory, MCP servers, custom tools, shell access, and optional
OpenProject automation behind a single CLI.

The main command is `o2d`. `open2deep` is provided as an alias.

## What It Does

- Runs as a REPL or one-shot CLI agent.
- Loads instruction memory from global and project-local files.
- Loads reusable skills and custom tools from local directories.
- Attaches MCP servers from JSON config files.
- Optionally exposes OpenProject project and work package tools when
  `OPENPROJECT_*` credentials are present.
- Preserves backward compatibility with older `ORDO_*` and `OPUS_*` naming.

## Installation

Open2Deep requires Python `3.11+`.

```bash
pip install -e .
```

After installation, the following commands are available:

```bash
o2d
open2deep
```

## Quick Start

Initialize the global home:

```bash
o2d init --global
```

Initialize project-local scaffolding in the current directory:

```bash
o2d init --project
```

Run the interactive shell:

```bash
o2d
```

Run a single request:

```bash
o2d "Summarize the current folder and suggest next tasks."
```

## Configuration

You can configure Open2Deep with environment variables or with
`~/.o2d/config.toml` and `./.o2d/config.toml`.

Typical LLM environment variables:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://your-llm-endpoint/v1"
export OPENAI_MODEL="Qwen3-Coder-480B-A35B-Instruct"
export OPENAI_MODEL_VISION="Llama-4-Scout"
```

Optional agent tuning:

```bash
export O2D_CONTEXT_WINDOW=128000
export O2D_ENABLE_EXECUTE=1
export O2D_MAX_ITEMS=25
export O2D_MAX_TEXT_CHARS=1600
```

Open2Deep also accepts legacy fallbacks such as `OPENAI_APIK_KEY`,
`ORDO_*`, and `OPUS_*`.

## Optional OpenProject Integration

If these values are set, OpenProject tools are attached automatically:

```bash
export OPENPROJECT_BASE_URL="https://your-openproject.example.com"
export OPENPROJECT_API_KEY="your-api-token"
```

The built-in OpenProject toolset covers:

- project listing and lookup
- project types, statuses, priorities, and assignees
- work package listing and lookup
- work package activity history
- work package creation, updates, and comments

## Directory Layout

Global home:

```text
~/.o2d/
  config.toml
  AGENTS_O2D.md
  PROMPT_O2D.md
  mcp_servers.json
  skills/
  tools/
```

Project-local files:

```text
./AGENTS_O2D.md
./.o2d/
  mcp_servers.json
  skills/
  tools/
```

## Loading Precedence

- Memory: `~/.o2d/AGENTS_O2D.md` -> `./AGENTS_O2D.md` ->
  `./.o2d/AGENTS_O2D.md` -> `./AGENTS.md`
- Skills: `~/.o2d/skills/` -> `./.o2d/skills/` -> `./skills/`
- Custom tools: `~/.o2d/tools/` -> `./.o2d/tools/` -> `./custom_tools/`
- MCP config: `~/.o2d/mcp_servers.json` -> `./.o2d/mcp_servers.json` ->
  `./mcp_servers.json`

Later paths override earlier ones when names collide.

## Useful Commands

```bash
o2d tools
o2d mcp
o2d doctor
```

Compatibility wrapper scripts are also included:

- `projects.py`
- `work_packages.py`
- `openproject_agent.py`

## Security Notes

- `mcp_servers.json`, `.env`, and local config files can contain secrets. Keep
  them local and do not commit them.
- OpenProject mutation tools perform real changes. Add approval rules in
  `AGENTS_O2D.md` when using production systems.

## Current Limits

- Session state is currently scoped to the in-process `thread_id`.
- This repository includes the framework and scaffolding; your local home and
  per-project secrets remain outside version control.
