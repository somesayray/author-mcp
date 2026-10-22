.PHONY: help build up down logs ps test test-cov health-check smoke-test index doctor serve atc

help:
	@echo "Author-MCP & ATC Make targets:"
	@echo "  make build       - Build the Author-MCP docker image"
	@echo "  make up          - Start Author-MCP & Author-Sessions stack"
	@echo "  make down        - Stop Author stack"
	@echo "  make logs        - View container logs"
	@echo "  make ps          - View container status"
	@echo "  make atc         - View Air Traffic Control status"
	@echo "  make index       - Index Books and text documents"
	@echo "  make doctor      - Run system doctor checks"
	@echo "  make serve       - Run local MCP server directly"
	@echo "  make test        - Run unit tests"
	@echo "  make health-check- Verify live health endpoint"
	@echo "  make smoke-test  - Run post-deploy smoke test"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

atc:
	python3 -m author_mcp.cli atc

index:
	python3 -m author_mcp.cli index

doctor:
	python3 -m author_mcp.cli doctor

serve:
	python3 -m author_mcp.cli serve

test:
	pytest tests/

health-check:
	@echo "Running Author-MCP health check..."
	@curl -sSf http://127.0.0.1:18083/health | python3 -m json.tool

smoke-test: health-check
