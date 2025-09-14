#!/usr/bin/env python
"""Main entry point for MCP server deployment."""

if __name__ == "__main__":
    from mcp_servers.immosearch_server import mcp
    mcp.run(transport="streamable-http")