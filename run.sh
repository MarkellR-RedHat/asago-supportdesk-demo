#!/usr/bin/env bash
# Start the four processes, run the MiDojo benchmark against Support Bot, tear down.
#   LLM_URL / LLM_KEY / LLM_MODEL  any OpenAI-compatible endpoint (vLLM, MaaS route, Ollama)
#   SUPPORTDESK_PROMPT_FIX=1       fix attempt 1: system prompt line
#   SUPPORTDESK_TOOL_FIX=1         fix attempt 2: rules enforced inside the email tool
set -euo pipefail
LLM_URL=${LLM_URL:-http://localhost:11434/v1}
LLM_KEY=${LLM_KEY:-none}
LLM_MODEL=${LLM_MODEL:-llama3.1:8b}
NAME=${1:-baseline}
mkdir -p runs/$NAME
pids=()
trap 'kill "${pids[@]}" 2>/dev/null || true' EXIT
wait_for() { for _ in $(seq 1 60); do curl -s -o /dev/null "$1" && return 0; sleep 1; done; echo "timeout: $1" >&2; exit 1; }

uv run supportdesk-real-mcp --port 8081 > runs/$NAME/real-mcp.log 2>&1 & pids+=($!)
uv run midojo-serve --suite supportdesk.suite_module --host 127.0.0.1 --port 8080 > runs/$NAME/control-plane.log 2>&1 & pids+=($!)
wait_for http://127.0.0.1:8080/suite
uv run supportdesk-fake-mcp --port 8082 --upstream-url http://localhost:8081/mcp > runs/$NAME/fake-mcp.log 2>&1 & pids+=($!)
LITELLM_API_KEY=$LLM_KEY LITELLM_API_URL=$LLM_URL LITELLM_MODEL=$LLM_MODEL \
  uv run supportdesk-agent --port 8000 --mcp-server-url http://localhost:8082/mcp > runs/$NAME/agent.log 2>&1 & pids+=($!)
wait_for http://127.0.0.1:8000/.well-known/agent-card.json

time uv run midojo-run --agent-uri http://localhost:8000 --protocol a2a \
  --suite supportdesk.suite_module --logdir runs/$NAME "${@:2}" 2>&1 | tee runs/$NAME/midojo-run.log
