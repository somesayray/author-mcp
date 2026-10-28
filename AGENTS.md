# AGENTS.md — mcp

> Role: **mcp** · Member of Enterprise Agentic Platform

## CR-CLI-ENTRY-001: Start with the CLI (CRITICAL — Org-Wide)

1. **Start with the CLI (CRITICAL ENTRY GATE)**: When receiving ANY request or starting any task, agents **MUST ALWAYS START WITH THE OPERATOR CLI (`hath0r`)** rather than inventing ad-hoc scripts.
2. **Missing Capability Offer**: If the required connection, MCP, workflow, bot, or factory does not exist in `hath0r`, offer to register the missing capability.
3. **Docs before code**: Require procedure/playbook/runbook before scaffolding implementation.

---

## Author MCP Knowledge & ATC Protocol (cr-author-mcp-001)

1. **Always Check Hath0r CLI First**: All agent reasoning and MCP health verification MUST start with `hath0r` CLI:
   - Check connection health: `hath0r mcp check`
   - List configured MCP servers: `hath0r mcp list`
   - Verify control tower status: `hath0r atc status`
2. **Leverage Author MCP for Knowledge Retrieval**: All knowledge and document queries across the Author suite MUST route through Author-MCP via Hath0r CLI:
   - Search knowledge: `hath0r mcp call author-mcp search_author_knowledge --args '{"query": "<query>", "limit": 5}'`
   - Fetch document content: `hath0r mcp call author-mcp get_author_document --args '{"doc_id": "<path-or-id>"}'`
   - List books & manuscripts: `hath0r mcp call author-mcp list_author_books --args '{"limit": 10}'`
   - Check tower status: `hath0r mcp call author-mcp atc_tower_status`
   - Search canonical FTS5 index: `hath0r kb search -q "<term>" --fts-only`
3. **MCP Connection Access**: The Hath0r framework maintains direct active connection to `author-mcp` (Priority 1 Root MCP) on port `18083` via `.hath0r/mcp.json`.
4. **Site-Free Policy**: Books is strictly text documents, codices, and manuscripts. NO web application or static site may be generated in this repository.

---

## Promotion Path (CR-BAI-001)

```text
local → development → testing → staging → master (Production)
```

## Branch Governance (cr-branch-gov-001)

- Issue first: create an issue before cutting a branch.
- Naming: `feature|bugfix|enhancement|chore/<issue-number>-slug`
- Base PR target: `development`

## AgentGraph Substrate

This repository is governed by the Hath0r AgentGraph substrate. Dynamic rule retrieval, role RBAC, and policy graphs are stored under `.hath0r/agentgraph/`.
- Query status: `hath0r agentgraph status`
- Query rules: `hath0r agentgraph query "<topic>"`
- Route role: `hath0r agentgraph route --role <role>`
- Validate rules: `hath0r agentgraph validate`

## Hyper Context Pointers
- **Src Subsystem**: `/Users/raybayly/Development/Projects/Author/mcp/src/AGENTS.md`
- **Contracts Subsystem**: `/Users/raybayly/Development/Projects/Author/mcp/contracts/AGENTS.md`
- **Docs Subsystem**: `/Users/raybayly/Development/Projects/Author/mcp/docs/AGENTS.md`
- **Tests Subsystem**: `/Users/raybayly/Development/Projects/Author/mcp/tests/AGENTS.md`
- **Cfg Subsystem**: `/Users/raybayly/Development/Projects/Author/mcp/cfg/AGENTS.md`

---

## CR-SONAR-PREANNOUNCE-001 (SonarCloud Thresholds Before Announcing Complete — CANONICAL)
- **Pre-Announcement SonarCloud Gate**: Before announcing any work as Complete, the agent MUST analyze the code and confirm it meets this repository's SonarCloud Quality Gate thresholds (coverage on new code, duplication, reliability, security, maintainability, and security hotspots reviewed).
- **How to Verify**: Use `hath0r quality sonar` (project key from `sonar-project.properties`) together with local test and coverage runs. If the gate cannot be checked, state that plainly instead of announcing Complete.
- **Not Complete Until Green**: A failing or unverified Quality Gate means the work is not Complete.
