# Author-MCP & ATC — Technical Specification

## 1. System Architecture

```text
                                  +-------------------+
                                  |   Hath0r / Agents |
                                  +---------+---------+
                                            |
                      (HTTP / JSON-RPC / MCP at :18083)
                                            |
                                            v
     +-----------------------------------------------------------------+
     |                     Author Air Traffic Control                  |
     |                       (author-net bridge)                       |
     |                                                                 |
     |   +-----------------------+           +---------------------+   |
     |   |      Author-MCP       |           |   Author-Sessions   |   |
     |   |   (Root MCP Engine)   +---------->+   (Redis Cache)     |   |
     |   +-----------+-----------+           +---------------------+   |
     |               |                                                 |
     +---------------+-------------------------------------------------+
                     |
         (Mounts Books /app/books)
                     |
                     v
     +-------------------------------+
     |             Books             |
     |      (Text Documents Only)    |
     +-------------------------------+
```

## 2. Ports & Networking
- **Docker Network**: `author-net`
- **Author-MCP Host Port**: `18083` (mapped to container port `8083`)
- **Author-Sessions (Redis)**: Internal port `6379`

## 3. Endpoints
- `GET /health`, `/healthz`, `/ready`: Health checks
- `GET /atc/status`: ATC Control Tower diagnostics
- `GET /atc/inventory`: Suite member repository inventory
- `GET /sources`: Indexed document sources summary
- `GET /documents`: List indexed text documents
- `POST /search`: BM25 text document search
- `POST /mcp`, `/rpc`: MCP JSON-RPC 2.0 protocol endpoint

## 4. Hath0r Governance
- **Canonical Root MCP**: Defined as Priority 1 in `.hath0r/mcp.json`.
- **Knowledgebase Sync**: Synced to `.hath0r/knowledgebase/documents/books`.
