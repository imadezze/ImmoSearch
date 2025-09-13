#!/usr/bin/env python
"""Simple STDIO client for testing MCP tools."""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.extra.run.context import RunContext
from mistralai.extra.mcp.stdio import MCPClientSTDIO, StdioServerParameters

# Load environment variables
load_dotenv()

# Config
MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

# MCP Server configuration
PROJECT_ROOT = Path(__file__).parent
SERVER_ARGS = [sys.executable, "-m", "mcp_servers.leboncoin_server"]

async def ainput(prompt: str = "") -> str:
    """Async-friendly input so the event loop stays responsive."""
    return await asyncio.to_thread(input, prompt)

async def main() -> None:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set")

    client = Mistral(api_key)

    print(f"🔌 Starting console chat with model: {MODEL}")
    print("💡 Tip: ask things that should use your MCP tools (e.g., 'Search properties in Le Bourget').")
    print("Type /exit to quit.\n")

    # Create server parameters for STDIO
    server_params = StdioServerParameters(
        command=SERVER_ARGS[0],
        args=SERVER_ARGS[1:],
        env=None
    )

    async with RunContext(model=MODEL) as run:
        # Use STDIO client for local MCP server
        mcp_client = MCPClientSTDIO(stdio_params=server_params)
        await run.register_mcp_client(mcp_client)

        # Get available tools
        tools = run.get_tools()

        def tool_name(t):
            return getattr(t, "name", getattr(getattr(t, "function", None), "name", "unknown"))

        tool_names = [tool_name(t) for t in tools]
        print(f"🧰 Tools available: {', '.join(tool_names) if tool_names else '(none found)'}\n")

        try:
            while True:
                user = (await ainput("you> ")).strip()
                if not user:
                    continue
                if user.lower() in {"/exit", "/quit"}:
                    break

                prompt = (
                    "If the request requires external info or actions, use the available MCP tools. "
                    "Otherwise answer directly.\n\n"
                    f"User: {user}"
                )

                result = await client.beta.conversations.run_async(
                    run_ctx=run, inputs=prompt
                )
                print(f"\nassistant> {result.output_as_text}\n")
        finally:
            await mcp_client.aclose()
            await asyncio.sleep(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass