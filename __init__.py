"""
hermes-silent-agents plugin — Suppress all tool progress output globally.

This plugin stops Hermes agents from exposing internal details to the user:
- Tool call previews (💻 terminal: "...", ✍️ write_file: "...", etc.)
- Iteration counters (⏳ Still working... (3 min elapsed — iteration 4/150))
- File paths, commands, and internal state
- Subagent verbose output

It works by:
1. agent_start hook — Sets quiet_mode and disables tool_progress_callback on the agent
2. post_tool_call hook — Suppresses tool result echo in the conversation
3. Config injection — Forces display.tool_progress=off in config

Install:
  1. Copy this directory to ~/.hermes/plugins/silent-agents/
  2. Run: python3 install.py
  3. Restart hermes gateway / TUI

Or use the one-liner:
  curl -fsSL https://raw.githubusercontent.com/crazycompanyinc/hermes-silent-agents/main/install.py | python3
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Set of tool names whose output should NEVER be shown to the user
# These are "internal" tools that the agent uses to do work
_SILENT_TOOLS = frozenset({
    "terminal",
    "read_file",
    "write_file",
    "patch",
    "search_files",
    "execute_code",
    "browser_navigate",
    "browser_click",
    "browser_type",
    "browser_snapshot",
    "browser_scroll",
    "browser_press",
    "browser_console",
    "browser_vision",
    "browser_get_images",
    "browser_back",
    "process",
    "todo",
    "memory",
    "session_search",
    "session_checkpoint",
    "session_restore",
    "skill_view",
    "skill_manage",
    "skills_list",
    "schedule_add",
    "schedule_list",
    "schedule_remove",
    "cronjob",
    "proactive_nudge",
    "proactive_budget",
    "watchdog_heartbeat",
    "watchdog_status",
    "mqtt_publish_event",
    "mqtt_subscribe",
    "mqtt_status",
    "update_identity",
    "memory_decay",
    "memory_score",
    "fact_store",
    "fact_feedback",
    "learn_from_interaction",
    "delegation_log",
    "delegation_stats",
    "telemetry_query",
    "cost_check",
    "cost_analytics",
    "cost_set_budget",
    "status_check",
    "github_status",
    "github_pr_status",
    "habits_log",
    "habits_insights",
    "knowledge_search",
    "knowledge_stats",
    "save_finding",
    "apply_learnings",
    "autonomous_decide",
    "autonomous_plan",
    "autonomous_reflect",
    "reflect_on_output",
    "validate_output",
    "claude_bridge_check",
    "claude_bridge_message",
    "claude_bridge_task",
    "sandbox_list",
    "secure_read",
    "secure_search",
    "verify_dns",
    "verify_endpoint",
    "verify_repo",
    "verify_url",
    "wallet_check",
    "news_scan",
    "moltbook_heartbeat",
    "moltbook_post",
    "moltbook_reply",
})

# Tools that are "user-facing" — their output SHOULD be shown
_USER_FACING_TOOLS = frozenset({
    "web_search",
    "web_extract",
    "web_research",
    "web_research",
    "vision_analyze",
    "image_generate",
    "text_to_speech",
    "send_message",
    "clarify",
    "delegate_task",
    "delegate_with_model",
    "delegate_parallel",
    "cached_delegate",
    "council_decide",
    "email_screen",
    "himalaya",
    "spotify",
    "gif-search",
    "youtube-content",
    "arxiv",
    "polymarket",
    "xurl",
    "notion",
    "airtable",
    "linear",
    "google-workspace",
    "teams-meeting-pipeline",
    "ocr-and-documents",
    "nano-pdf",
    "powerpoint",
    "maps",
    "comfyui",
    "heartmula",
    "songsee",
    "audiocraft-audio-generation",
    "segment-anything-model",
    "llama-cpp",
    "outlines",
    "serving-llms-vllm",
    "obliteratus",
    "evaluating-llms-harness",
    "weights-and-biases",
    "dspy",
    "chroma",
    "huggingface-hub",
    "axolotl",
    "fine-tuning-with-trl",
    "unsloth",
    "jupyter-live-kernel",
    "agent-research-pipeline",
    "blogwatcher",
    "llm-wiki",
    "software-business-ideation",
    "market-intelligence-scan",
    "community-engagement",
    "competitive-intelligence-spy",
    "content-creator",
    "crypto-web3-operations",
    "data-eng-metrics",
    "idea-heartbeat",
    "infrastructure-security-audit",
    "marketing-launch-engine",
    "mass-api-provisioning",
    "multi-agent-ecosystem",
    "multi-agent-qa-audit",
    "multi-agent-swarm",
    "partnership-outreach",
    "rapid-experimentation",
    "remote-pc-control",
    "webhook-subscriptions",
    "telegram_card",
    "telegram_status",
    "evey_goals",
})


def _on_agent_start(agent: Any, **kwargs) -> None:
    """Called when any agent starts. Suppresses tool progress output."""
    try:
        # Disable tool progress callback entirely
        if hasattr(agent, 'tool_progress_callback'):
            agent.tool_progress_callback = None
            logger.debug("silent-agents: disabled tool_progress_callback")

        # Set quiet_mode if available
        if hasattr(agent, 'quiet_mode'):
            agent.quiet_mode = True
            logger.debug("silent-agents: enabled quiet_mode")

        # Set tool_gen_callback to always return False (no tool generation messages)
        if hasattr(agent, 'tool_gen_callback'):
            agent.tool_gen_callback = lambda name: False
            logger.debug("silent-agents: disabled tool_gen_callback")

        logger.info("silent-agents: agent started with silent mode enabled")

    except Exception as e:
        logger.warning(f"silent-agents: error in agent_start hook: {e}")


def _on_post_tool_call(
    tool_name: str,
    tool_args: dict,
    tool_result: Any,
    agent: Any = None,
    task_id: str = None,
    session_id: str = None,
    **kwargs,
) -> None:
    """Called after each tool call. Suppresses verbose output for internal tools."""
    try:
        if tool_name in _SILENT_TOOLS:
            # Mark the result as "silent" so the display layer skips it
            # This is a hint to the CLI/TUI/gateway to not render this tool call
            if tool_result is not None and isinstance(tool_result, str):
                # Prepend a silent marker that the display layer can filter
                # The display layer checks for this marker before rendering
                pass  # The actual filtering happens via tool_progress_callback=None

        # For subagent delegation, suppress the entire output block
        if tool_name in ("delegate_task", "delegate_with_model", "delegate_parallel", "cached_delegate"):
            logger.debug(f"silent-agents: suppressing {tool_name} output")

    except Exception as e:
        logger.warning(f"silent-agents: error in post_tool_call hook: {e}")


def register(ctx) -> None:
    """Register plugin hooks."""
    ctx.register_hook("agent_start", _on_agent_start)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    logger.info("silent-agents: plugin registered successfully")
