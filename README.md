# Status Monitor

A lightweight macOS menu bar app that shows live per-component operational status for **Anthropic** and **Composio**. The dot in your menu bar turns 🟠/🔴 the moment any component degrades.

## What it monitors

| Service | Components |
|---|---|
| Anthropic | claude.ai, Claude Console, Claude API, Claude Code, Claude Cowork, Claude for Government |
| Composio | v3 API, Tool Execution, Triggers V1/V2, Tool Search, Sandbox, Proxy, Auth providers, Connect MCP, CLI, Connections, Dashboard |
| Buffer | Buffer Website, Web App, iOS App, Android App, Buffer API, API Developer Portal, Buffer MCP |

Polls every **60 seconds** automatically. Click any service row to open its status page.

## Option A — Run from source (requires Python 3)

```bash
git clone https://github.com/fcastrosantosapliqo/status-monitor
cd status-monitor
bash setup.sh
./run.sh
```

To auto-launch at login:

```bash
./run.sh --install
```

To remove the login item:

```bash
./run.sh --uninstall
```

## Option B — Standalone .app bundle (no Python needed)

Build a self-contained double-click app:

```bash
bash setup.sh
.venv/bin/pip install py2app
.venv/bin/python setup.py py2app
```

The app is created at `dist/Status Monitor.app`. Zip and share it. On first open, recipients will see an *unidentified developer* warning — right-click → Open → Open to approve it once.

## Status icons

| Icon | Meaning |
|---|---|
| 🟢 | All systems operational |
| 🟡 | Minor incident |
| 🟠 | Major incident |
| 🔴 | Critical outage |
| ⚪ | Status page unreachable |

## Requirements

- macOS 12 or later
- Python 3.10+ (only needed for Option A / building the .app)
