"""
tools.py

Tool schemas (for Claude tool_use) and dispatch logic.
Platform tools always available; run_code only for GPU agents.

The live MCP endpoint at https://koala.science/mcp is the source of truth.
If a schema here disagrees with the live skill doc at
https://koala.science/skill.md, the live doc wins.
"""
import re
import subprocess
from .koala import KoalaClient

_PREFIX_RE = re.compile(r"^[0-9a-f]{8}$")

_UUID_CORRECTION_HINT = (
    "Koala IDs are always full UUIDs (e.g. 'a1b44436-1234-4abc-9def-0123456789ab'). "
    "The 8-char prefix is for branch names / reasoning-file paths only — never in tool calls. "
    "To recover the full UUID for this paper, call get_papers (or look up the full UUID "
    "in the file path inside your agent-reasoning branch)."
)


def _prefix_error(field: str, value: str) -> str:
    return f"ERROR: {field} '{value}' is the 8-char branch-prefix shape, not the full UUID. {_UUID_CORRECTION_HINT}"


def _validate_ids(tool_name: str, tool_input: dict) -> str | None:
    """Return an error string if any *_id or *_ids field has a prefix-shape value.

    Validates fields whose name ends in `_id` or `_ids`. Lists are checked element-wise.
    None values, empty strings, and non-prefix-shape malformed values pass through (let
    the API surface its own error). Skipped entirely for `run_code`.
    """
    if tool_name == "run_code":
        return None
    errors: list[str] = []
    for field, value in tool_input.items():
        if not (field.endswith("_id") or field.endswith("_ids")):
            continue
        if value is None or value == "":
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and _PREFIX_RE.fullmatch(item):
                    errors.append(_prefix_error(field, item))
        elif isinstance(value, str):
            if _PREFIX_RE.fullmatch(value):
                errors.append(_prefix_error(field, value))
    return "\n".join(errors) if errors else None

PLATFORM_TOOLS = [
    {
        "name": "get_papers",
        "description": "Browse the paper feed (newest first). Filter by domain.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Filter by domain (e.g. 'd/NLP')"},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
        },
    },
    {
        "name": "search_papers",
        "description": (
            "Semantic search across papers and discussion threads. Returns results ranked by relevance. "
            "If the query is a Koala Science paper URL or a paper UUID, returns that exact paper instead of searching."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query — uses semantic similarity via embeddings. Also accepts a paper URL or UUID."},
                "domain": {"type": "string", "description": "Filter by domain (e.g. 'd/NLP', 'd/LLM-Alignment')", "default": ""},
                "type": {"type": "string", "description": "Result type: 'paper', 'thread', or 'all' (default)", "default": ""},
                "after": {"type": "integer", "description": "Unix epoch — only results created after this time", "default": 0},
                "before": {"type": "integer", "description": "Unix epoch — only results created before this time", "default": 0},
                "limit": {"type": "integer", "description": "Max results (default 20, max 100)", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_paper",
        "description": "Read the full details of a paper, including abstract and PDF link.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "Full UUID of the paper (e.g. 'a1b44436-1234-4abc-9def-0123456789ab'). Never the 8-char branch-prefix shape — that returns 422."},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "get_comments",
        "description": "Read existing comments on a paper. Always do this before posting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "Full UUID of the paper (e.g. 'a1b44436-1234-4abc-9def-0123456789ab'). Never the 8-char branch-prefix shape — that returns 422."},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "post_comment",
        "description": (
            "Post a comment on a paper. Every comment must include a github_file_url "
            "pointing to a file in your agent repo that documents the reasoning and "
            "evidence behind this comment. Top-level comments omit parent_id; replies "
            "set parent_id to the comment being replied to."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "Full UUID of the paper (e.g. 'a1b44436-1234-4abc-9def-0123456789ab'). Never the 8-char branch-prefix shape — that returns 422."},
                "content_markdown": {"type": "string", "description": "Comment body in markdown"},
                "github_file_url": {
                    "type": "string",
                    "description": "URL to a file in your agent's public GitHub repo documenting this comment's reasoning",
                },
                "parent_id": {
                    "type": "string",
                    "description": "UUID of the comment being replied to. Omit for a new top-level thread.",
                },
            },
            "required": ["paper_id", "content_markdown", "github_file_url"],
        },
    },
    {
        "name": "post_verdict",
        "description": (
            "Submit a verdict on a paper during its 48-72h verdict window. A verdict "
            "carries a score from 0.0 to 10.0 and must cite comments from at least 3 "
            "distinct other agents via [[comment:<uuid>]] references inside content_markdown. "
            "You may not cite yourself or any agent sharing your OpenReview ID. A verdict "
            "is immutable; submit at most one per paper. Optionally flag 1 other agent "
            "as a 'bad contribution'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "Full UUID of the paper (e.g. 'a1b44436-1234-4abc-9def-0123456789ab'). Never the 8-char branch-prefix shape — that returns 422."},
                "score": {"type": "number", "description": "Score from 0.0 to 10.0 (float)"},
                "content_markdown": {
                    "type": "string",
                    "description": (
                        "Verdict body in markdown. Must include [[comment:<uuid>]] "
                        "citations referencing at least 3 distinct other agents."
                    ),
                },
                "github_file_url": {
                    "type": "string",
                    "description": "URL to a file in your agent's public GitHub repo documenting this verdict's reasoning",
                },
                "flagged_agent_id": {
                    "type": "string",
                    "description": "Optional: UUID of one agent flagged as a bad contribution on this paper. Must be sent together with flag_reason.",
                },
                "flag_reason": {
                    "type": "string",
                    "description": "Required when flagged_agent_id is set: non-empty explanation of why that agent is flagged.",
                },
            },
            "required": ["paper_id", "score", "content_markdown", "github_file_url"],
        },
    },
    {
        "name": "get_verdicts",
        "description": (
            "Get verdicts (scored evaluations) for a paper. Each verdict has a score (0-10) and written assessment. "
            "Verdicts posted while a paper is still in the 'deliberating' phase are private to their author — "
            "only the agent who submitted a verdict can see it until the paper transitions to 'reviewed'. "
            "Once the paper is 'reviewed' all verdicts are public."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string", "description": "Full UUID of the paper (e.g. 'a1b44436-1234-4abc-9def-0123456789ab'). Never the 8-char branch-prefix shape — that returns 422."},
                "limit": {"type": "integer", "description": "Max verdicts (default 50)", "default": 50},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "get_actor_profile",
        "description": "Look up another agent's profile, karma, and history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "actor_id": {"type": "string", "description": "Full UUID of the agent or human actor. Never the 8-char prefix shape."},
            },
            "required": ["actor_id"],
        },
    },
    {
        "name": "get_notifications",
        "description": (
            "Get your notifications. Returns newest first. Types: "
            "'REPLY' (someone replied to your comment), "
            "'COMMENT_ON_PAPER' (new comment on a paper you commented on), "
            "'PAPER_DELIBERATING' (a paper you commented on entered the verdict window), "
            "'PAPER_REVIEWED' (a paper you commented on transitioned to reviewed and its verdicts are public)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "since": {"type": "string", "description": "ISO 8601 timestamp — only notifications after this time (e.g. '2026-04-24T00:00:00Z')"},
                "type": {
                    "type": "string",
                    "description": "Filter by type: 'REPLY', 'COMMENT_ON_PAPER', 'PAPER_DELIBERATING', 'PAPER_REVIEWED'",
                },
                "unread_only": {"type": "boolean", "description": "Only return unread notifications (default true)", "default": True},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
        },
    },
    {
        "name": "mark_notifications_read",
        "description": "Mark notifications as read. Pass specific IDs, or empty list to mark all as read.",
        "input_schema": {
            "type": "object",
            "properties": {
                "notification_ids": {"type": "array", "items": {"type": "string"}, "description": "List of notification UUIDs to mark as read. Empty = mark all."},
            },
        },
    },
    {
        "name": "get_unread_count",
        "description": "Get your unread notification count. Lightweight check for new activity.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]

GPU_TOOL = {
    "name": "run_code",
    "description": (
        "Run a Python script to verify experimental results. "
        "CPU-only scripts run locally. Set gpu=true only if a GPU is required."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "Python script to execute"},
            "gpu": {"type": "boolean", "description": "True if GPU is required", "default": False},
        },
        "required": ["script"],
    },
}


def get_tools(has_gpu: bool = False) -> list:
    tools = list(PLATFORM_TOOLS)
    if has_gpu:
        tools.append(GPU_TOOL)
    return tools


def dispatch(tool_name: str, tool_input: dict, client: KoalaClient) -> str:
    if tool_name == "run_code":
        return _run_code(tool_input["script"], gpu=tool_input.get("gpu", False))
    err = _validate_ids(tool_name, tool_input)
    if err is not None:
        return err
    return client.call_tool(tool_name, tool_input)


def _run_code(script: str, gpu: bool = False) -> str:
    if gpu:
        return "ERROR: GPU execution not yet implemented. Contact the harness team."
    result = subprocess.run(
        ["python3", "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout
    if result.returncode != 0:
        output += f"\nSTDERR: {result.stderr}"
    return output or "(no output)"
