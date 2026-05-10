#!/usr/bin/env python3
"""
hermes-silent-agents installer
Installs the plugin, patches delegate_tool.py, and configures Hermes to suppress all tool progress output.

Usage:
  python3 install.py          # Install plugin + configure + patch
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

# Path to the delegate_tool.py that needs patching
DELEGATE_TOOL_PATH = Path("/usr/local/lib/hermes-agent/tools/delegate_tool.py")

PATCH_MARKER = "# === SILENT-AGENTS PATCH START ==="
PATCH_END_MARKER = "# === SILENT-AGENTS PATCH END ==="

PATCH_CODE = '''
# === SILENT-AGENTS PATCH START ===
    # Silent-agents: check if tool_progress is off before building callback
    try:
        _sa_cfg = _load_config()
        _sa_display = _sa_cfg.get("display") or {}
        _sa_tp = _sa_display.get("tool_progress", "all")
        if _sa_tp is False or str(_sa_tp).strip().lower() == "off":
            return None  # Silent mode — no progress callback at all
    except Exception:
        pass
# === SILENT-AGENTS PATCH END ===

'''


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

    display["tool_progress"] = "off"
    display["tool_preview_length"] = 0
    display["cleanup_progress"] = True

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
    print(f"  Config updated: display.tool_progress = off (all platforms)")


def configure_tui() -> None:
    """Set HERMES_TUI_TOOL_PROGRESS=off in .env"""
    env_path = HERMES_HOME / ".env"
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    lines = [l for l in lines if not l.startswith("HERMES_TUI_TOOL_PROGRESS=")]
    lines.append("HERMES_TUI_TOOL_PROGRESS=off")
    env_path.write_text("\n".join(lines) + "\n")
    print(f"  TUI config: HERMES_TUI_TOOL_PROGRESS=off")


def patch_delegate_tool() -> None:
    """Patch delegate_tool.py to suppress subagent progress when tool_progress=off"""
    if not DELEGATE_TOOL_PATH.exists():
        print(f"  WARNING: {DELEGATE_TOOL_PATH} not found, skipping patch")
        return

    content = DELEGATE_TOOL_PATH.read_text()

    # Check if already patched
    if PATCH_MARKER in content:
        print("  delegate_tool.py already patched")
        return

    # Find the _build_child_progress_callback function
    # Insert our check right after the "if not spinner and not parent_cb:" check
    target = '''    if not spinner and not parent_cb:
        return None  # No display → no callback → zero behavior change'''

    if target not in content:
        print("  WARNING: Could not find patch target in delegate_tool.py")
        return

    # Insert the silent-agents check BEFORE the existing early return
    # This way, even if spinner/callback exist, we return None when silent
    replacement = '''    # Silent-agents: suppress all subagent progress when tool_progress=off
    try:
        _sa_cfg = _load_config()
        _sa_display = _sa_cfg.get("display") or {}
        _sa_tp = _sa_display.get("tool_progress", "all")
        if _sa_tp is False or str(_sa_tp).strip().lower() == "off":
            return None  # Silent mode — no progress callback at all
    except Exception:
        pass

    if not spinner and not parent_cb:
        return None  # No display → no callback → zero behavior change'''

    content = content.replace(target, replacement)
    DELEGATE_TOOL_PATH.write_text(content)
    print(f"  Patched: {DELEGATE_TOOL_PATH}")


def unpatch_delegate_tool() -> None:
    """Remove the silent-agents patch from delegate_tool.py"""
    if not DELEGATE_TOOL_PATH.exists():
        return

    content = DELEGATE_TOOL_PATH.read_text()
    if PATCH_MARKER not in content:
        print("  delegate_tool.py not patched")
        return

    # Remove the patch block
    lines = content.splitlines()
    new_lines = []
    in_patch = False
    for line in lines:
        if PATCH_MARKER in line:
            in_patch = True
            continue
        if PATCH_END_MARKER in line:
            in_patch = False
            continue
        if not in_patch:
            new_lines.append(line)

    DELEGATE_TOOL_PATH.write_text("\n".join(new_lines))
    print(f"  Unpatched: {DELEGATE_TOOL_PATH}")


def add_plugin_to_config() -> None:
    """Add silent-agents to plugins.enabled list"""
    config = load_config()
    if "plugins" not in config:
        config["plugins"] = {}
    if "enabled" not in config["plugins"]:
        config["plugins"]["enabled"] = []

    enabled = config["plugins"]["enabled"]
    # Check if already added (handle both string and dict entries)
    already = any(
        (isinstance(e, str) and e == "silent-agents") or
        (isinstance(e, dict) and "silent-agents" in e)
        for e in enabled
    )
    if not already:
        enabled.append("silent-agents")
        save_config(config)
        print("  Added silent-agents to plugins.enabled")
    else:
        print("  silent-agents already in plugins.enabled")


def remove_plugin_from_config() -> None:
    """Remove silent-agents from plugins.enabled list"""
    config = load_config()
    if "plugins" not in config or "enabled" not in config["plugins"]:
        return

    enabled = config["plugins"]["enabled"]
    new_enabled = [
        e for e in enabled
        if not ((isinstance(e, str) and e == "silent-agents") or
                (isinstance(e, dict) and "silent-agents" in e))
    ]
    config["plugins"]["enabled"] = new_enabled
    save_config(config)
    print("  Removed silent-agents from plugins.enabled")


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

    delegate_patched = False
    if DELEGATE_TOOL_PATH.exists():
        delegate_patched = PATCH_MARKER in DELEGATE_TOOL_PATH.read_text()

    in_config = False
    if "plugins" in config and "enabled" in config["plugins"]:
        in_config = any(
            (isinstance(e, str) and e == "silent-agents") or
            (isinstance(e, dict) and "silent-agents" in e)
            for e in config["plugins"]["enabled"]
        )

    print("=== hermes-silent-agents status ===")
    print(f"  Plugin installed: {plugin_installed}")
    print(f"  In plugins.enabled: {in_config}")
    print(f"  display.tool_progress: {tool_progress}")
    print(f"  display.tool_preview_length: {preview_length}")
    print(f"  display.cleanup_progress: {cleanup}")
    print(f"  TUI tool_progress: {tui_progress}")
    print(f"  delegate_tool.py patched: {delegate_patched}")
    print()

    all_good = (
        tool_progress == "off" and
        plugin_installed and
        in_config and
        tui_progress == "off" and
        delegate_patched
    )
    if all_good:
        print("  STATUS: Silent mode is FULLY ACTIVE")
    else:
        print("  STATUS: Silent mode is NOT fully configured")
        print("  Run: python3 install.py")


def uninstall() -> None:
    """Remove plugin and restore default config"""
    if PLUGINS_DIR.exists():
        shutil.rmtree(PLUGINS_DIR)
        print(f"  Removed plugin: {PLUGINS_DIR}")

    remove_plugin_from_config()
    unpatch_delegate_tool()

    config = load_config()
    if "display" in config:
        display = config["display"]
        if display.get("tool_progress") == "off":
            display["tool_progress"] = "all"
            print("  Restored: display.tool_progress = all")
        if display.get("cleanup_progress") == True:
            display.pop("cleanup_progress", None)
            print("  Removed: display.cleanup_progress")
        if "platforms" in display:
            for plat, settings in list(display["platforms"].items()):
                if isinstance(settings, dict) and "tool_progress" in settings:
                    del settings["tool_progress"]
                    print(f"  Removed: display.platforms.{plat}.tool_progress")
        save_config(config)

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

    print("[1/5] Installing plugin...")
    install_plugin()
    print()

    print("[2/5] Adding to plugins.enabled...")
    add_plugin_to_config()
    print()

    print("[3/5] Configuring display settings...")
    configure_display()
    print()

    print("[4/5] Configuring TUI...")
    configure_tui()
    print()

    print("[5/5] Patching delegate_tool.py for subagent silence...")
    patch_delegate_tool()
    print()

    print("=== Installation complete ===")
    print()
    print("Restart hermes gateway/TUI to apply changes:")
    print("  systemctl --user restart hermes-gateway")
    print()
    print("To verify: python3 install.py --check")
    print("To uninstall: python3 install.py --uninstall")


if __name__ == "__main__":
    main()
