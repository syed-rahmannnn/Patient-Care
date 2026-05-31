# Claude CLI (terminal)

This folder contains a tiny terminal helper to call Anthropic's Claude HTTP API from the command line.

Files
- `claude.sh`: a small bash wrapper that builds a JSON payload and posts it to the Anthropic endpoint using `curl`.

Prerequisites
- An Anthropic API key. Set it in your shell as `ANTHROPIC_API_KEY`.
- Either `jq` (recommended) or `python3` available in PATH.

Usage
- Make the script executable (once):

```bash
chmod +x tools/claude.sh
```

- Run with a prompt as arguments:

```bash
export ANTHROPIC_API_KEY="sk-..."
tools/claude.sh "Summarize the following text: ..."
```

- Or pipe input:

```bash
echo "Write a two-sentence haiku about code" | tools/claude.sh
```

Environment variables (optional)
- `CLAUDE_MODEL` — model name (default `claude-2.1`)
- `CLAUDE_ENDPOINT` — HTTP endpoint (default `https://api.anthropic.com/v1/complete`)
- `CLAUDE_MAX_TOKENS` — token limit for the request (default `800`)

Notes
- The script tries to print the common response fields (`completion`, `output`, `choices`, etc.). If the HTTP schema differs, open the raw response to debug.
- This helper is intentionally minimal; you can extend it to add streaming, files, or richer CLI flags.
