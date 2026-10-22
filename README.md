# Author-MCP & Air Traffic Control (ATC)

**Root Model Context Protocol (MCP) Server & Suite Control Tower**

> Technical Reference: See [TECH_README.md](TECH_README.md) for architecture, subsystem maps, and specifications.

---

## 🌟 Overview & Architecture

`author-mcp` serves two foundational roles for the `Author` project:

1. **Root MCP Server (Priority 1)**:
   - Indexes and exposes the entire `Books` repository text documents, manuscripts, outlines, and lore.
   - Provides fast semantic and BM25 search across all book chapters and author notes.
   - Syncs knowledge directly into `.hath0r/knowledgebase`.
   - Exposes streamable-http JSON-RPC 2.0 endpoints for agents, Claude Desktop, and Antigravity.

2. **Air Traffic Control (ATC) Control Tower**:
   - Central infrastructure controller for the `Author` suite (`mcp` + `Books`).
   - Manages Docker Compose stack: `Author-MCP` and `Author-Sessions` (Redis) on network `author-net`.
   - Monitors member repo git states, container health, and task dispatching.

---

## 🚀 Quick Start

### 1. Run with Docker (Recommended)
```sh
# Build container image
make build

# Start the stack (Author-MCP + Author-Sessions)
make up

# Check status and health
make ps
make health-check
make atc
```

### 2. Run with Hath0r CLI & Local Python
```sh
# Doctor check
hath0r doctor

# Start local server directly
python3 -m author_mcp serve --port 18083

# Index documents
python3 -m author_mcp index
```

---

## 🛠️ MCP Tools Exposed

| Tool Name | Description |
|-----------|-------------|
| `search_author_knowledge` | Search across indexed books, manuscripts, chapters, outlines, and lore. |
| `get_author_document` | Retrieve full text of any manuscript or book document. |
| `list_author_books` | List all indexed books, chapters, and text documents. |
| `atc_tower_status` | Retrieve Air Traffic Control status for the Author suite. |
| `sync_knowledge_to_hathor` | Sync indexed documents into `.hath0r/knowledgebase`. |
| `get_session_memory` | Retrieve session memory from Redis container. |
| `set_session_memory` | Store session memory in Redis container. |

---

## License

Apache License 2.0
