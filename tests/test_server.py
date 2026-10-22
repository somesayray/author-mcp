"""Unit tests for Author-MCP server and MCP JSON-RPC protocol."""

import pytest
from httpx import AsyncClient, ASGITransport
from author_mcp.server import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Author-MCP"
    assert data["role"] == "Root MCP & ATC"


@pytest.mark.asyncio
async def test_mcp_info_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/mcp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Author-MCP"
    assert data["tools_count"] > 0


@pytest.mark.asyncio
async def test_mcp_tools_list_rpc():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/list",
            "params": {},
        }
        resp = await ac.post("/mcp", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["id"] == "1"
    tool_names = [t["name"] for t in res["result"]["tools"]]
    assert "search_author_knowledge" in tool_names
    assert "get_author_document" in tool_names
    assert "list_author_books" in tool_names
    assert "atc_tower_status" in tool_names


@pytest.mark.asyncio
async def test_atc_status_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/atc/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert data["suite"] == "Author"
