"""FastAPI Server for Author-MCP implementing Model Context Protocol and ATC endpoints.

Brought over from Hath0r Enterprise Knowledgebase & Index Architecture.
Exposes both canonical Hath0r KB tools (kb_search, kb_get_document, kb_index_list, etc.)
and specialized Author tools (search_author_knowledge, get_author_document, atc_tower_status).
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from author_mcp import __version__
from author_mcp.atc import AuthorATC
from author_mcp.config import settings
from author_mcp.core.models import Document
from author_mcp.indexer import KnowledgeIndexer
from author_mcp.runbooks.service import RunbookService
from author_mcp.session import SessionManager

logger = structlog.get_logger(__name__)

indexer = KnowledgeIndexer()
session_mgr = SessionManager()
atc = AuthorATC()
runbook_svc = RunbookService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    logger.info(
        "starting_author_mcp_server",
        version=__version__,
        env=settings.ENVIRONMENT,
        redis=settings.REDIS_URL,
    )
    if settings.ENVIRONMENT != "test":
        asyncio.create_task(asyncio.to_thread(indexer.scan_and_index))

    yield
    await session_mgr.close()
    logger.info("stopped_author_mcp_server")


app = FastAPI(
    title="Author-MCP Server & ATC",
    description="Enterprise Model Context Protocol Server, Knowledge Hub & Air Traffic Control for Author Suite",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REST Models
# ============================================================================


class SearchRequest(BaseModel):
    query: str
    index_name: str | None = None
    source: str | None = None
    category: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class SessionSetRequest(BaseModel):
    key: str
    value: Any
    ttl_seconds: int | None = None


class IndexCreateRequest(BaseModel):
    index_name: str
    description: str = ""


class AddDocumentRequest(BaseModel):
    id: str
    content: str
    index_name: str = "books"
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# REST Endpoints
# ============================================================================


@app.get("/health")
@app.get("/healthz")
@app.get("/ready")
async def health_check():
    redis_healthy = await session_mgr.ping()
    stats = indexer.storage.get_stats()
    return {
        "status": "healthy",
        "service": "Author-MCP",
        "role": "Root MCP & ATC",
        "version": __version__,
        "environment": settings.ENVIRONMENT,
        "indexed_documents": stats.total_documents,
        "indexed_chunks": stats.total_chunks,
        "indices_count": len(stats.indices),
        "session_redis_connected": redis_healthy,
        "books_dir": str(settings.BOOKS_DIR),
        "books_dir_exists": settings.BOOKS_DIR.exists(),
    }


@app.get("/atc/status")
async def atc_status():
    """Retrieve full Air Traffic Control (ATC) status."""
    return atc.get_atc_status()


@app.get("/atc/inventory")
async def atc_inventory():
    """Retrieve ATC suite inventory."""
    return atc.get_inventory()


@app.get("/indices")
@app.get("/kb/indices")
async def list_indices():
    """List all configured knowledge indices."""
    return {"indices": [i.model_dump() for i in indexer.storage.list_indices()]}


@app.post("/indices")
@app.post("/kb/indices")
async def create_index(req: IndexCreateRequest):
    """Create a new knowledge index."""
    info = indexer.storage.create_index(req.index_name, req.description)
    return info.model_dump()


@app.get("/sources")
async def list_sources():
    """List all configured knowledge sources and their indexed document counts."""
    return indexer.get_sources_summary()


@app.post("/import")
async def trigger_import(force: bool = False):
    """Trigger indexing of all Books and Author context folders."""
    res = indexer.scan_and_index(force=force)
    return res


@app.get("/documents")
async def list_documents(index_name: str | None = None, category: str | None = None):
    """List all indexed documents."""
    return {"documents": indexer.list_documents(index_name=index_name, category=category)}


@app.post("/documents")
async def add_document(req: AddDocumentRequest):
    """Add or upsert a document into an index."""
    docs = indexer.pipeline.index_text(
        content=req.content,
        doc_id=req.id,
        index_name=req.index_name,
        metadata=req.metadata,
        chunk=True,
    )
    return {"status": "success", "chunks_created": len(docs)}


@app.post("/search")
async def search_knowledge(req: SearchRequest):
    """Search author knowledgebase documents."""
    results = indexer.search(
        query=req.query,
        index_name=req.index_name,
        source=req.source,
        category=req.category,
        limit=req.limit,
    )
    return {
        "query": req.query,
        "count": len(results),
        "results": results,
    }


@app.get("/documents/{doc_id:path}")
async def get_document(doc_id: str, index_name: str | None = None):
    doc = indexer.get_document(doc_id, index_name=index_name)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.get("/runbooks")
async def list_runbooks():
    """List available operational runbooks."""
    return {"runbooks": [r.model_dump() for r in runbook_svc.list_runbooks()]}


@app.post("/session/set")
async def set_session(req: SessionSetRequest):
    ok = await session_mgr.set_value(req.key, req.value, req.ttl_seconds)
    return {"status": "ok" if ok else "error"}


@app.get("/session/get/{key}")
async def get_session(key: str):
    val = await session_mgr.get_value(key)
    return {"key": key, "value": val}


@app.post("/knowledge/sync")
async def sync_knowledge(target_dir: str | None = None):
    """Synchronize indexed knowledgebase into .hath0r/knowledgebase."""
    target_path = Path(target_dir) if target_dir else None
    res = indexer.sync_to_hathor_knowledgebase(target_dir=target_path)
    return res


# ============================================================================
# Model Context Protocol (MCP) JSON-RPC 2.0 Handler
# ============================================================================

MCP_TOOLS = [
    # Author Core Tools
    {
        "name": "search_author_knowledge",
        "description": "Search across all indexed books, manuscripts, chapters, outlines, notes, lore, and text documents in the Author suite.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query terms or keywords"},
                "index_name": {"type": "string", "description": "Target index (books, lore, characters, outlines, notes)"},
                "category": {"type": "string", "description": "Filter by category (manuscript, lore, characters, outlines, notes)"},
                "limit": {"type": "integer", "default": 5, "description": "Maximum number of results to return"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_author_document",
        "description": "Retrieve full text content and metadata of a specific manuscript, chapter, or text document by its document ID or relative path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "Document ID or relative path"},
                "index_name": {"type": "string", "description": "Optional index name"},
            },
            "required": ["doc_id"],
        },
    },
    {
        "name": "list_author_books",
        "description": "List all books, manuscripts, chapters, and text documents currently indexed in the Author library.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index_name": {"type": "string", "description": "Optional index filter"},
                "category": {"type": "string", "description": "Optional category filter"},
            },
        },
    },
    {
        "name": "atc_tower_status",
        "description": "Retrieve Air Traffic Control (ATC) operational status, member repo health, and container stack for the Author suite.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "sync_knowledge_to_hathor",
        "description": "Synchronize all indexed author knowledge and book text documents into .hath0r/knowledgebase single source of truth.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_dir": {"type": "string", "description": "Optional custom target directory"},
            },
        },
    },
    # Hath0r Suite Canonical KB Tools
    {
        "name": "kb_search",
        "description": "Enterprise BM25 search across indexed documents with category and index filtering and snippet highlights.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "index_name": {"type": "string", "description": "Target index (books, lore, characters, outlines, notes)"},
                "category": {"type": "string", "description": "Filter by category"},
                "limit": {"type": "integer", "default": 5, "description": "Max results"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "kb_get_document",
        "description": "Retrieve document text, word counts, reading time, and metadata by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "Document ID"},
                "index_name": {"type": "string", "description": "Optional index name"},
            },
            "required": ["doc_id"],
        },
    },
    {
        "name": "kb_index_list",
        "description": "List all knowledge base indices, document counts, chunk counts, and storage metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "kb_index_create",
        "description": "Create a new partitioned knowledge index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index_name": {"type": "string", "description": "Name of the new index"},
                "description": {"type": "string", "description": "Index description"},
            },
            "required": ["index_name"],
        },
    },
    {
        "name": "kb_add_document",
        "description": "Add or upsert a document into a knowledge index with automatic chunking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Unique document identifier"},
                "content": {"type": "string", "description": "Full document content"},
                "index_name": {"type": "string", "default": "books", "description": "Target index name"},
                "metadata": {"type": "object", "description": "Optional custom metadata dict"},
            },
            "required": ["id", "content"],
        },
    },
    {
        "name": "kb_index_directory",
        "description": "Execute the indexing pipeline on a directory of text documents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dir_path": {"type": "string", "description": "Directory path to index"},
                "index_name": {"type": "string", "description": "Optional target index"},
            },
            "required": ["dir_path"],
        },
    },
    {
        "name": "kb_stats",
        "description": "Retrieve global knowledge base statistics, chunk totals, and index breakdowns.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "runbook_list",
        "description": "List standard operating procedures (SOPs) and runbooks for author workflows.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Optional search filter"},
            },
        },
    },
    {
        "name": "get_session_memory",
        "description": "Retrieve a session variable or working memory from the Author-Sessions Redis container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The session key"},
            },
            "required": ["key"],
        },
    },
    {
        "name": "set_session_memory",
        "description": "Store a session variable or working memory into the Author-Sessions Redis container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The session key"},
                "value": {"type": "string", "description": "The value or JSON string to store"},
                "ttl_seconds": {"type": "integer", "description": "Optional TTL in seconds"},
            },
            "required": ["key", "value"],
        },
    },
]


@app.get("/mcp")
async def mcp_info():
    """Information endpoint for Model Context Protocol."""
    stats = indexer.storage.get_stats()
    return {
        "name": "Author-MCP",
        "role": "Root MCP Server & Air Traffic Control",
        "version": __version__,
        "transport": "streamable-http",
        "tools_count": len(MCP_TOOLS),
        "total_documents": stats.total_documents,
        "total_chunks": stats.total_chunks,
        "indices": list(stats.indices.keys()),
    }


@app.post("/mcp")
@app.post("/rpc")
async def mcp_rpc(request: Request):
    """MCP JSON-RPC 2.0 endpoint."""
    body = await request.json()
    msg_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": MCP_TOOLS},
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name in ("search_author_knowledge", "kb_search"):
                res = indexer.search(
                    query=args.get("query", ""),
                    index_name=args.get("index_name"),
                    source=args.get("source"),
                    category=args.get("category"),
                    limit=args.get("limit", 5),
                )
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res, indent=2)}]
                    },
                }

            elif tool_name in ("get_author_document", "kb_get_document"):
                doc = indexer.get_document(args.get("doc_id", ""), index_name=args.get("index_name"))
                if not doc:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": "Document not found"}]
                        },
                    }
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": doc.get("content", "")}],
                        "metadata": {
                            "title": doc.get("title"),
                            "index": doc.get("index"),
                            "category": doc.get("category"),
                            "word_count": doc.get("word_count"),
                            "reading_time_minutes": doc.get("reading_time_minutes"),
                            "path": doc.get("path"),
                            "tags": doc.get("tags"),
                        },
                    },
                }

            elif tool_name == "list_author_books":
                docs = indexer.list_documents(index_name=args.get("index_name"), category=args.get("category"))
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(docs, indent=2)}]
                    },
                }

            elif tool_name == "atc_tower_status":
                status = atc.get_atc_status()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(status, indent=2)}]
                    },
                }

            elif tool_name in ("sync_knowledge_to_hathor", "kb_sync_all"):
                target = args.get("target_dir")
                res = indexer.sync_to_hathor_knowledgebase(
                    target_dir=Path(target) if target else None
                )
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res, indent=2)}]
                    },
                }

            elif tool_name == "kb_index_list":
                indices = [i.model_dump() for i in indexer.storage.list_indices()]
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(indices, indent=2, default=str)}]
                    },
                }

            elif tool_name == "kb_index_create":
                info = indexer.storage.create_index(args.get("index_name", ""), args.get("description", ""))
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(info.model_dump(), indent=2, default=str)}]
                    },
                }

            elif tool_name == "kb_add_document":
                docs = indexer.pipeline.index_text(
                    content=args.get("content", ""),
                    doc_id=args.get("id", ""),
                    index_name=args.get("index_name", "books"),
                    metadata=args.get("metadata"),
                    chunk=True,
                )
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Indexed {len(docs)} chunks successfully."}]
                    },
                }

            elif tool_name == "kb_index_directory":
                dir_path = args.get("dir_path", "")
                res = indexer.pipeline.index_directory(
                    dir_path=dir_path,
                    index_name=args.get("index_name"),
                )
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res, indent=2)}]
                    },
                }

            elif tool_name == "kb_stats":
                stats = indexer.storage.get_stats()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(stats.model_dump(), indent=2, default=str)}]
                    },
                }

            elif tool_name == "runbook_list":
                query = args.get("query")
                rbs = runbook_svc.search_runbooks(query) if query else runbook_svc.list_runbooks()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps([r.model_dump() for r in rbs], indent=2)}]
                    },
                }

            elif tool_name == "get_session_memory":
                val = await session_mgr.get_value(args.get("key", ""))
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(val) if val is not None else "null"}]
                    },
                }

            elif tool_name == "set_session_memory":
                ok = await session_mgr.set_value(
                    args.get("key", ""),
                    args.get("value"),
                    args.get("ttl_seconds"),
                )
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": "ok" if ok else "error"}]
                    },
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                }

        except Exception as e:
            logger.error("tool_execution_failed", tool=tool_name, error=str(e))
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32000, "message": str(e)},
            }

    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "Author-MCP",
                    "version": __version__,
                },
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }
