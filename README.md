# 🤫 hermes-silent-agents

**Stop Hermes agents from exposing internal tool calls, paths, commands, and iteration details to the user.**

## The Problem

When Hermes agents work, they expose everything:

```
[CV BUILDER]: 💻 terminal: "which pdflatex 2>/dev/null && echo..."
[CV BUILDER]: ✍️ write_file: "/root/.hermes/profiles/cv-builder/cac..."
[CV BUILDER]: ⏳ Still working... (3 min elapsed — iteration 4/150)
[CV BUILDER]: 💻 terminal: "apt-get update -qq && apt-get install..."
[CV BUILDER]: 🔧 patch: "/root/.hermes/profiles/cv-builder/cac..."
[CV BUILDER]: ⏳ Still working... (6 min elapsed — iteration 7/150)
```

This is noise. Users should only see:
- The agent's actual responses
- Final results
- Progress summaries (if anything)

## The Solution

This plugin + config package:

1. **Plugin** (`silent-agents`) — Hooks into `agent_start` and `post_tool_call` to suppress tool progress callbacks
2. **Config** — Sets `display.tool_progress: off` globally and per-platform
3. **TUI** — Sets `HERMES_TUI_TOOL_PROGRESS=off` in `.env`

Works for **all agents**: main agent, subagents, delegated agents, cron jobs.

## Install

### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/crazycompanyinc/hermes-silent-agents/main/install.py | python3
```

### Manual

```bash
git clone https://github.com/crazycompanyinc/hermes-silent-agents.git
cd hermes-silent-agents
python3 install.py
```

### Verify

```bash
python3 install.py --check
```

### Uninstall

```bash
python3 install.py --uninstall
```

## What It Changes

### `~/.hermes/config.yaml`

```yaml
display:
  tool_progress: "off"        # Was "all"
  tool_preview_length: 0      # Was 0 (unlimited)
  cleanup_progress: true      # New: auto-delete progress bubbles
  platforms:
    telegram:
      tool_progress: "off"    # Was "all"
      tool_preview_length: 0
    discord:
      tool_progress: "off"    # Was "all"
      tool_preview_length: 0
    # ... all platforms
```

### `~/.hermes/.env`

```
HERMES_TUI_TOOL_PROGRESS=off
```

### Plugin

Installs to `~/.hermes/plugins/silent-agents/`:
- `plugin.yaml` — Plugin manifest
- `__init__.py` — Hook implementations

## How It Works

### 1. Plugin Hooks

The plugin registers two hooks:

**`agent_start`** — When any agent starts:
- Sets `agent.tool_progress_callback = None` (disables all tool progress messages)
- Sets `agent.quiet_mode = True` (suppresses internal output)
- Sets `agent.tool_gen_callback = lambda name: False` (no tool generation messages)

**`post_tool_call`** — After each tool call:
- Identifies "internal" tools (terminal, read_file, write_file, patch, etc.)
- Marks their output as silent so the display layer skips rendering

### 2. Config

The `display.tool_progress` setting controls tool progress visibility:

| Value | Behavior |
|-------|----------|
| `"all"` | Show all tool calls with previews (default, noisy) |
| `"new"` | Show only first use of each tool |
| `"off"` | Show nothing (silent mode) |
| `"verbose"` | Show everything including args (debug mode) |

### 3. Per-Platform Overrides

Different platforms have different defaults:

| Platform | Default | After Plugin |
|----------|---------|--------------|
| Telegram | `"all"` | `"off"` |
| Discord | `"all"` | `"off"` |
| Slack | `"off"` | `"off"` |
| Signal | `"off"` | `"off"` |
| TUI | `"all"` | `"off"` (via env var) |

## Result

**Before:**
```
[AGENT]: 💻 terminal: "cd /root/projects && npm install"
[AGENT]: ⏳ Still working... (2 min elapsed — iteration 3/150)
[AGENT]: ✍️ write_file: "/root/projects/app/src/index.ts"
[AGENT]: 💻 terminal: "npm run build"
[AGENT]: ⏳ Still working... (5 min elapsed — iteration 8/150)
[AGENT]: 🔧 patch: "/root/projects/app/src/index.ts"
[AGENT]: Done! The app is ready at /root/projects/app/dist/
```

**After:**
```
[AGENT]: Building the app... Done! The app is ready.
```

## Compatibility

- Hermes Agent >= 2026.5.x
- Works with: CLI, TUI, Telegram, Discord, Slack, Signal, WhatsApp, Matrix, all platforms
- Works with: subagents, delegated agents, cron jobs, ACP sessions

## Files

```
hermes-silent-agents/
├── plugin.yaml          # Plugin manifest
├── __init__.py          # Hook implementations
├── install.py           # Installer script
└── README.md            # This file
```

## License

MIT
