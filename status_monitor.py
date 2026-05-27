#!/usr/bin/env python3
"""
Apliqo Status Monitor — per-component status for Anthropic, Composio and Buffer.

Usage:
  ./run.sh                  run the app
  ./run.sh --install        install as a login item (auto-start)
  ./run.sh --uninstall      remove login item
"""

import sys
import threading
import webbrowser
from datetime import datetime

import requests
import rumps

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SERVICES = [
    {
        "name": "Anthropic",
        "components_api": "https://status.claude.com/api/v2/components.json",
        "web": "https://status.claude.com",
        "provider": "statuspage",
    },
    {
        "name": "Composio",
        # status.composio.dev is the current page (composio.instatus.com is outdated)
        "components_api": "https://status.composio.dev/components.json",
        "web": "https://status.composio.dev",
        "provider": "instatus",
    },
    {
        "name": "Buffer",
        "components_api": "https://status.buffer.com/api/v2/components.json",
        "web": "https://status.buffer.com",
        "provider": "statuspage",
    },
]

REFRESH_INTERVAL = 60  # seconds

# Severity from highest to lowest
SEVERITY_ORDER = ["critical", "major", "minor", "none", "unknown"]

ICONS = {
    "none":     "🟢",
    "minor":    "🟡",
    "major":    "🟠",
    "critical": "🔴",
    "unknown":  "⚪",
}

# Statuspage.io component status → normalised level
STATUSPAGE_MAP = {
    "operational":          "none",
    "degraded_performance": "minor",
    "partial_outage":       "major",
    "major_outage":         "critical",
    "under_maintenance":    "minor",
}

# Instatus component status → normalised level
INSTATUS_MAP = {
    "OPERATIONAL":      "none",
    "UNDERMAINTENANCE": "minor",
    "DEGRADED":         "minor",
    "PARTIALOUTAGE":    "major",
    "MAJOROUTAGE":      "critical",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def normalize(raw: str, provider: str) -> str:
    if provider == "statuspage":
        return STATUSPAGE_MAP.get(raw.lower(), "unknown")
    return INSTATUS_MAP.get(raw.upper(), "unknown")


def worst(levels: list[str]) -> str:
    def rank(lvl: str) -> int:
        try:
            return SEVERITY_ORDER.index(lvl)
        except ValueError:
            return len(SEVERITY_ORDER)
    return min(levels, key=rank, default="unknown")


def fetch_components(svc: dict) -> list[tuple[str, str]]:
    """Returns [(component_name, normalised_level), ...]"""
    try:
        resp = requests.get(svc["components_api"], timeout=10)
        resp.raise_for_status()
        data = resp.json()
        provider = svc["provider"]

        if provider == "instatus":
            comps = data.get("components", [])
            # IDs that appear as a parent group → they are headers, not real components
            parent_ids = {c["group"]["id"] for c in comps if c.get("group")}
            return [
                (c["name"], normalize(c["status"], "instatus"))
                for c in comps
                if c["id"] not in parent_ids
            ]
        else:
            comps = data.get("components", [])
            # group=True rows are section headers on Statuspage.io
            return [
                (c["name"], normalize(c["status"], "statuspage"))
                for c in comps
                if not c.get("group", False)
            ]
    except Exception as exc:
        return [(f"Error: {type(exc).__name__}", "unknown")]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class StatusMonitor(rumps.App):
    def __init__(self):
        super().__init__(ICONS["unknown"], quit_button=None)
        self._headers: dict[str, rumps.MenuItem] = {}
        self._comp_items: dict[str, dict[str, rumps.MenuItem]] = {}
        self._initialized: set[str] = set()
        self._last_updated: rumps.MenuItem | None = None
        # Pending results written by background thread, consumed on main thread
        self._pending: dict | None = None
        self._lock = threading.Lock()
        self._build_menu()
        # Runs on Cocoa main thread — safe for all UI mutations
        rumps.Timer(self._apply_pending, 0.5).start()
        # Triggers background network fetches
        rumps.Timer(self._on_fetch_timer, REFRESH_INTERVAL).start()
        self._do_refresh()

    # --- Menu skeleton ------------------------------------------------------

    def _build_menu(self):
        for svc in SERVICES:
            header = rumps.MenuItem(
                f"{ICONS['unknown']} {svc['name']}",
                callback=lambda _, s=svc: webbrowser.open(s["web"]),
            )
            self._headers[svc["name"]] = header
            self._comp_items[svc["name"]] = {}
            self.menu.add(header)

        self.menu.add(None)
        # Give it a no-op callback so rumps treats it as a live item
        self._last_updated = rumps.MenuItem("Last checked: —", callback=lambda _: None)
        self.menu.add(self._last_updated)
        self.menu.add(None)
        self.menu.add(rumps.MenuItem("Refresh Now", callback=self._on_refresh_clicked))
        self.menu.add(None)
        self.menu.add(
            rumps.MenuItem("Quit Status Monitor", callback=lambda _: rumps.quit_application())
        )

    # --- Callbacks ----------------------------------------------------------

    def _on_fetch_timer(self, _):
        self._do_refresh()

    def _on_refresh_clicked(self, _):
        self.title = "⏳"
        self._do_refresh()

    # --- Fetch (background thread — no UI calls here) -----------------------

    def _do_refresh(self):
        threading.Thread(target=self._fetch_all, daemon=True).start()

    def _fetch_all(self):
        results = {svc["name"]: (svc, fetch_components(svc)) for svc in SERVICES}
        with self._lock:
            self._pending = results

    # --- UI update (main thread via 0.5 s polling timer) --------------------

    def _apply_pending(self, _):
        with self._lock:
            if self._pending is None:
                return
            results = self._pending
            self._pending = None
        self._update_ui(results)

    def _update_ui(self, results: dict):
        all_indicators: list[str] = []

        for svc_name, (svc, components) in results.items():
            indicators = [lvl for _, lvl in components]
            all_indicators.extend(indicators)
            svc_icon = ICONS.get(worst(indicators) if indicators else "unknown", ICONS["unknown"])

            self._headers[svc_name].title = f"{svc_icon} {svc_name}"
            comp_map = self._comp_items[svc_name]

            if svc_name not in self._initialized:
                # First fetch: populate sub-menu with real component items
                for comp_name, level in components:
                    icon = ICONS.get(level, ICONS["unknown"])
                    item = rumps.MenuItem(f"  {icon}  {comp_name}")
                    self._headers[svc_name].add(item)
                    comp_map[comp_name] = item
                self._initialized.add(svc_name)
            else:
                # Subsequent fetches: update icons in-place
                for comp_name, level in components:
                    if comp_name in comp_map:
                        icon = ICONS.get(level, ICONS["unknown"])
                        comp_map[comp_name].title = f"  {icon}  {comp_name}"

        self.title = ICONS.get(worst(all_indicators), ICONS["unknown"])
        self._last_updated.title = f"Last checked: {datetime.now().strftime('%H:%M:%S')}"


# ---------------------------------------------------------------------------
# Login-item installer
# ---------------------------------------------------------------------------
LAUNCH_AGENT_LABEL = "com.apliqo.statusmonitor"
PLIST_PATH = (
    f"/Users/{__import__('os').environ.get('USER', 'user')}"
    f"/Library/LaunchAgents/{LAUNCH_AGENT_LABEL}.plist"
)


def install_launcher():
    import os, subprocess

    script_dir = os.path.dirname(os.path.abspath(__file__))
    run_sh = os.path.join(script_dir, "run.sh")
    if os.path.exists(run_sh):
        program_args = f"        <string>{run_sh}</string>"
    else:
        python = sys.executable
        script = os.path.abspath(__file__)
        program_args = (
            f"        <string>{python}</string>\n"
            f"        <string>{script}</string>"
        )

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCH_AGENT_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
{program_args}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/status_monitor.log</string>
</dict>
</plist>"""

    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    with open(PLIST_PATH, "w") as f:
        f.write(plist)

    subprocess.run(["launchctl", "load", PLIST_PATH], check=True)
    print(f"✅  Installed. Status Monitor will launch at every login.")
    print(f"    Plist: {PLIST_PATH}")
    print(f"    Logs:  /tmp/status_monitor.log")


def uninstall_launcher():
    import os, subprocess

    if os.path.exists(PLIST_PATH):
        subprocess.run(["launchctl", "unload", PLIST_PATH], check=False)
        os.remove(PLIST_PATH)
        print("✅  Uninstalled. Status Monitor will no longer launch at login.")
    else:
        print("ℹ️   No login item found.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if "--install" in sys.argv:
        install_launcher()
    elif "--uninstall" in sys.argv:
        uninstall_launcher()
    else:
        StatusMonitor().run()
