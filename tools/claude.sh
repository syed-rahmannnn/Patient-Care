#!/usr/bin/env bash
set -euo pipefail

# Simple Claude CLI using curl and Anthropic HTTP API
# Reads API key from ANTHROPIC_API_KEY and optional environment vars

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Error: set ANTHROPIC_API_KEY environment variable with your Anthropic API key." >&2
  exit 1
fi

# Model, endpoint and token limit defaults (user can override via env)
MODEL="${CLAUDE_MODEL:-claude-2.1}"
ENDPOINT="${CLAUDE_ENDPOINT:-https://api.anthropic.com/v1/complete}"
MAX_TOKENS="${CLAUDE_MAX_TOKENS:-800}"

# Read prompt: either from arguments or from stdin
if [[ $# -gt 0 ]]; then
  PROMPT="$*"
else
  # read entire stdin
  PROMPT=$(cat -)
fi

if [[ -z "$PROMPT" ]]; then
  echo "Usage: claude.sh <prompt>" >&2
  echo "Or: echo '<prompt>' | claude.sh" >&2
  exit 2
fi

# Build JSON payload. Prefer jq if available for safe escaping, otherwise use python to build JSON.
if command -v jq >/dev/null 2>&1; then
  PAYLOAD=$(jq -n --arg model "$MODEL" --arg prompt "$PROMPT" --argjson max_tokens "$MAX_TOKENS" '{model:$model, prompt:$prompt, max_tokens_to_sample:$max_tokens}')
else
  if command -v python3 >/dev/null 2>&1; then
    PAYLOAD=$(python3 - <<PY
import json,sys
model = sys.argv[1]
prompt = sys.argv[2]
max_tokens = int(sys.argv[3])
print(json.dumps({"model":model, "prompt":prompt, "max_tokens_to_sample":max_tokens}))
PY
    -- "$MODEL" "$PROMPT" "$MAX_TOKENS")
  else
    echo "Error: install 'jq' or 'python3' to build the JSON payload." >&2
    exit 3
  fi
fi

# Call the Anthropic API
HTTP_RESPONSE=$(curl -sS -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -d "$PAYLOAD")

# Try to extract the generated text. Many Anthropic responses have a 'completion' field.
if command -v jq >/dev/null 2>&1; then
  echo "$HTTP_RESPONSE" | jq -r '.completion // .output // .choices[0].text // .choices[0].message.content // "(no completion field)"'
else
  # best-effort: print whole response
  echo "$HTTP_RESPONSE"
fi
