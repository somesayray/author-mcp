# AGENTS.md — mcp

> Governed by Hath0r AgentGraph, MemoryGraph (`CR-MEMORY-COMPOUND-001`), and Automatic Task Evaluations (`CR-TASK-EVAL-001`).

---

## CR-CONTEXT-SQUEEZE-001: Compress Context with SuperSqueeze (CRITICAL — Org-Wide · CANONICAL)

1. **Squeeze before you load**: Bulky context (whole files, logs, CI/tool output, KB/RAG hits, transcripts, anything over ~2,000 tokens) MUST go through SuperSqueeze before it enters an agent's context or a prompt: `hath0r squeeze -q "<active query>" -f <file>` (or `-c "<text>"`), or `SuperSqueezeBot` in code. No hand-rolled truncation.
2. **Anchor on the active query** and re-squeeze when the query changes.
3. **Quality floor**: if `verifier.quality_score` < 0.90, lower `--threshold` or switch to targeted reads (line ranges, `grep`, `hath0r code`); never dump the whole source.
4. **Local-first**: use `--local` for sensitive content; never squeeze secrets.
5. **Exact-text exceptions**: code being edited, diffs under review, quoted legal text and fixtures are read verbatim with targeted reads.
6. **Pipelines route through SuperSqueeze** (`CAGEngine.pack_context()`, `HybridCAGRAGRouter`, HAHP envelopes, MCP responses); audited by `SubstrateUtilizationBot` and the Tier 2 eval.

Canonical: [HATH0R-CLI `docs/governance/rules/cr-context-squeeze-001.md`](https://github.com/Bayly-AI/HATH0R-CLI/blob/development/docs/governance/rules/cr-context-squeeze-001.md).

## CR-CLI-ENTRY-001: Start with the CLI (CRITICAL — Org-Wide · CANONICAL)

1. **Start with the CLI (CRITICAL ENTRY GATE)**: When receiving ANY request or starting any task, agents **MUST ALWAYS START WITH THE OPERATOR CLI (`hath0r`)** rather than inventing ad-hoc scripts. Check `hath0r --help` and the matching `hath0r <group> --help` first.
2. **Missing Capability Offer**: If the required connection, MCP, workflow, bot, or factory does not exist in `hath0r`, offer to register the missing capability, using the original request as the acceptance test.
3. **Docs before code**: Require procedure/playbook/runbook before scaffolding implementation.

Canonical: [HATH0R-CLI `docs/governance/cli-first-rules.md`](https://github.com/Bayly-AI/HATH0R-CLI/blob/development/docs/governance/cli-first-rules.md).

## CR-TASK-EVAL-001 (Automatic Task Evaluation Before Announcing Complete — CRITICAL · CANONICAL)
- **Mandatory Pre-Announcement Task Evaluation Gate**: Every task MUST be evaluated across the 4-tier hybrid evaluation pipeline (Tier 1 Deterministic Rubrics, Tier 2 Trajectory & FinOps Efficiency, Tier 3 Adversarial & Diff Critics, Tier 4 Goal Alignment & Consensus) prior to announcing work as Complete.
- **Composite Reward Threshold**: Task completion requires `passed_gate: true` and composite reward score `R_task >= 0.80` persisted in `.hath0r/evals/latest.json` and compounded as an `eval:<task_id>` node in `.hath0r/memory/graph.json`.
- **How to Verify**: Run `hath0r evals run` and `hath0r evals verify` before announcing Complete (`EndOfTaskBot`, `TaskAnnouncerBot.announce_complete`, and `CleanReposWorkflowBot` enforce this gate automatically).
- **Mandatory Eval Scorecard Summary After Every Task (CRITICAL · CANONICAL)**: Immediately after running task evaluations (`hath0r evals run`), the agent MUST always return a structured summary of the **Eval Scorecard** (`eval_id`, `task_id`, `passed_gate`, composite `R_task`, Tier 1–4 scores, and `.hath0r/evals/latest.json` path) in its completion response to the user.
- **Not Complete Until Evaluated & Scorecard Returned**: A missing, failing, unverified, or unreported task evaluation scorecard means the work is not Complete.
