# asago-supportdesk-demo

A throwaway customer support agent, the one-page AI policy it is supposed to follow, and the
[asago](https://github.com/asago-ai) tooling that checks whether it does.

- `policy/support-ai-policy.md` is the policy. `asago-policy-mapper` reads it and maps it to risks in the IBM AI Risk Atlas.
- `supportdesk/` is Support Bot: an A2A agent with three MCP tools (`get_customer`, `get_order_status`, `send_followup_email`).
- `supportdesk/suite.yaml` and `supportdesk/fake_mcp.py` are the [MiDojo](https://github.com/asago-ai/midojo) suite and
  interception layer that red-team Support Bot against those risks.
- `deploy/` runs the same thing on OpenShift.

Support Bot works with any OpenAI-compatible endpoint: a vLLM server, a Red Hat OpenShift AI
Models-as-a-Service route, or Ollama on a laptop.

## Run it

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/MarkellRawls/asago-supportdesk-demo && cd asago-supportdesk-demo
uv sync

export LLM_URL=https://<your-vllm-or-maas-route>/v1
export LLM_KEY=<api key>
export LLM_MODEL=<served model name>

./run.sh baseline                                                # the agent as built
SUPPORTDESK_PROMPT_FIX=1 ./run.sh prompt-fix                     # fix 1: a line in the system prompt
SUPPORTDESK_PROMPT_FIX=1 SUPPORTDESK_TOOL_FIX=1 ./run.sh tool-fix  # fix 2: rules enforced inside the email tool
```

`run.sh` starts four processes (the real MCP server, the MiDojo control plane, the fake MCP server, the agent),
runs `midojo-run`, and writes everything to `runs/<name>/`.

Reading the results table: **Utility** is whether the agent still did the job it was asked to do. **Security** shows
whether each injected attack succeeded, and the percentage at the bottom is the share of attacks that **succeeded**,
so lower is better. `N/A` means that user task never read the poisoned field.

## Map the policy to risks

```bash
git clone https://github.com/asago-ai/asago-policy-mapper && git clone --branch v1.2.3 https://github.com/IBM/ai-atlas-nexus
cd asago-policy-mapper && uv sync
uv run asago-policy-mapper extract ../asago-supportdesk-demo/policy/support-ai-policy.md \
  -o ../asago-supportdesk-demo/policy/output \
  --base-url $LLM_URL --api-key $LLM_KEY --model $LLM_MODEL \
  --nexus-base-dir ../ai-atlas-nexus
```

## On OpenShift

These manifests build with `kubectl kustomize` but have not been applied to a live cluster yet, so expect to adjust them. The results in the blog post came from `run.sh` on a laptop, pointed at a model served on OpenShift.

```bash
podman build -t quay.io/<you>/asago-supportdesk-demo:latest -f Containerfile . && podman push quay.io/<you>/asago-supportdesk-demo:latest
# edit images: in deploy/kustomization.yaml
oc new-project asago-supportdesk
oc create secret generic supportdesk-llm-creds \
  --from-literal=LITELLM_API_KEY=... --from-literal=LITELLM_API_URL=https://<route>/v1 --from-literal=LITELLM_MODEL=<model>
oc apply -k deploy
oc logs -f job/supportdesk-redteam
```

To test a fix, set `SUPPORTDESK_PROMPT_FIX` / `SUPPORTDESK_TOOL_FIX` to `"1"` in the manifests, then
`oc delete job supportdesk-redteam && oc apply -k deploy`.

## Credits

`supportdesk/agent.py` is adapted from the MiDojo weather example agent (Apache-2.0). MiDojo is pinned to commit `8ffbee4`.
