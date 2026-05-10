#!/usr/bin/env python3
"""
hermes-silent-agents installer
Installs the plugin and configures Hermes to suppress all tool progress output.

Usage:
  python3 install.py          # Install plugin + configure
  python3 install.py --check  # Check current status
  python3 install.py --uninstall  # Remove plugin + restore defaults
"""

import os
import sys
import shutil
import yaml
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
CONFIG_PATH = HERMES_HOME / "config.yaml"
PLUGINS_DIR = HERMES_HOME / "plugins" / "silent-agents"
PLUGIN_SOURCE = Path(__file__).parent


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def install_plugin() -> None:
    """Copy plugin files to ~/.hermes/plugins/silent-agents/"""
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    # Copy plugin files
    for fname in ("plugin.yaml", "__init__.py"):
        src = PLUGIN_SOURCE / fname
        dst = PLUGINS_DIR / fname
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied {fname} -> {dst}")

    print(f"  Plugin installed at: {PLUGINS_DIR}")


def configure_display() -> None:
    """Set display.tool_progress=off and tool_preview_length=0 in config.yaml"""
    config = load_config()

    if "display" not in config:
        config["display"] = {}

    display = config["display"]

    # Store previous values for rollback
    prev_tool_progress = display.get("tool_progress", "all")
    prev_preview_length = display.get("tool_preview_length", 0)

    display["tool_progress"] = "off"
    display["tool_preview_length"] = 0
    display["cleanup_progress"] = True

    # Also set per-platform overrides for all platforms
    if "platforms" not in display:
        display["platforms"] = {}

    platforms = [
        "telegram", "discord", "slack", "signal", "whatsapp",
        "matrix", "mattermost", "feishu", "weixin", "wecom",
        "dingtalk", "email", "sms", "webhook", "api_server",
        "homeassistant", "bluebubbles", "wecom_callback",
    ]

    for plat in platforms:
        if plat not in display["platforms"]:
            display["platforms"][plat] = {}
        display["platforms"][plat]["tool_progress"] = "off"
        display["platforms"][plat]["tool_preview_length"] = 0

    save_config(config)
    print(f"  Config updated: display.tool_progress = off")
    print(f"  Config updated: display.tool_preview_length = 0")
    print(f"  Config updated: cleanup_progress = true")
    print(f"  Config updated: all platforms set to tool_progress=off")


def configure_tui() -> None:
    """Set HERMES_TUI_TOOL_PROGRESS=off in .env"""
    env_path = HERMES_HOME / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    # Remove existing HERMES_TUI_TOOL_PROGRESS line
    lines = [l for l in lines if not l.startswith("HERMES_TUI_TOOL_PROGRESS=")]
    lines.append("HERMES_TUI_TOOL_PROGRESS=off")

    env_path.write_text("\n".join(lines) + "\n")
    print(f"  TUI config: HERMES_TUI_TOOL_PROGRESS=off")


def check_status() -> None:
    """Check current configuration status"""
    config = load_config()
    display = config.get("display", {})

    tool_progress = display.get("tool_progress", "all (default)")
    preview_length = display.get("tool_preview_length", "0 (default)")
    cleanup = display.get("cleanup_progress", "false (default)")

    plugin_installed = PLUGINS_DIR.exists()

    env_path = HERMES_HOME / ".env"
    tui_progress = "not set"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("HERMES_TUI_TOOL_PROGRESS="):
                tui_progress = line.split("=", 1)[1]

    print("=== hermes-silent-agents status ===")
    print(f"  Plugin installed: {plugin_installed}")
    print(f"  display.tool_progress: {tool_progress}")
    print(f"  display.tool_preview_length: {preview_length}")
    print(f"  display.cleanup_progress: {cleanup}")
    print(f"  TUI tool_progress: {tui_progress}")
    print()

    if tool_progress == "off" and plugin_installed:
        print("  STATUS: Silent mode is ACTIVE")
    else:
        print("  STATUS: Silent mode is NOT fully configured")
        print("  Run: python3 install.py")


def uninstall() -> None:
    """Remove plugin and restore default config"""
    if PLUGINS_DIR.exists():
        shutil.rmtree(PLUGINS_DIR)
        print(f"  Removed plugin: {PLUGINS_DIR}")

    config = load_config()
    if "display" in config:
        display = config["display"]

        # Restore defaults
        if display.get("tool_progress") == "off":
            display["tool_progress"] = "all"
            print("  Restored: display.tool_progress = all")

        if display.get("tool_preview_length") == 0:
            display["tool_preview_length"] = 0  # Keep 0, it's fine

        if display.get("cleanup_progress") == True:
            display.pop("cleanup_progress", None)
            print("  Removed: display.cleanup_progress")

        # Remove per-platform tool_progress overrides
        if "platforms" in display:
            for plat, settings in list(display["platforms"].items()):
                if isinstance(settings, dict) and "tool_progress" in settings:
                    del settings["tool_progress"]
                    print(f"  Removed: display.platforms.{plat}.tool_progress")

        save_config(config)

    # Remove TUI env
    env_path = HERMES_HOME / ".env"
    if env_path.exists():
        lines = env_path.read_text().splitlines()
        lines = [l for l in lines if not l.startswith("HERMES_TUI_TOOL_PROGRESS=")]
        env_path.write_text("\n".join(lines) + "\n")
        print("  Removed: HERMES_TUI_TOOL_PROGRESS")

    print("  Uninstalled. Restart hermes to apply changes.")


def main():
    if "--check" in sys.argv:
        check_status()
        return

    if "--uninstall" in sys.argv:
        print("Uninstalling hermes-silent-agents...")
        uninstall()
        return

    print("Installing hermes-silent-agents...")
    print()

    print("[1/3] Installing plugin...")
    install_plugin()
    print()

    print("[2/3] Configuring display settings...")
    configure_display()
    print()

    print("[3/3] Configuring TUI...")
    configure_tui()
    print()

    print("=== Installation complete ===")
    print()
    print("Restart hermes gateway/TUI to apply changes:")
    print("  hermes gateway restart")
    print("  or")
    print("  hermes --tui  (will pick up new settings)")
    print()
    print("To verify: python3 install.py --check")
    print("To uninstall: python3 install.py --uninstall")


if __name__ == "__main__":
    main()
