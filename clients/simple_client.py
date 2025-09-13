#!/usr/bin/env python
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.extra.mcp.sse import MCPClientSSE, SSEServerParams
from mistralai.extra.run.context import RunContext

# --- Config ---
MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
server_url = os.getenv("SERVER_URL", "http://127.0.0.1:8000/sse")

# Point this to YOUR MCP server (pick ONE of the two styles below)
PROJECT_ROOT = Path(__file__).parent
# 1) Run a module (preferred if your server is a package: mcp_servers/stdio_server.py + __init__.py present)
SERVER_ARGS = ["-m", "mcp_servers.dvf_server"]
# 2) Or run a file directly (uncomment and adjust)
# SERVER_ARGS = [str((PROJECT_ROOT / "mcp_servers" / "stdio_server.py").resolve())]
# --------------

load_dotenv()


async def ainput(prompt: str = "") -> str:
    """Async-friendly input so the event loop stays responsive."""
    return await asyncio.to_thread(input, prompt)


# ... (imports and setup above unchanged)


async def main() -> None:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set")

    client = Mistral(api_key)

    print(f"🔌 Starting console chat with model: {MODEL}")
    print(
        "💡 Tip: ask things that should use your MCP tools (e.g., 'Generate Leboncoin URL for Paris' or 'Search properties in Le Bourget')."
    )
    print("Type /exit to quit.\n")

    async with RunContext(model=MODEL) as run:
        mcp_client = MCPClientSSE(
            sse_params=SSEServerParams(url=server_url, timeout=100)
        )
        await run.register_mcp_client(mcp_client)

        # ✅ NEW: use get_tools()
        tools = run.get_tools()

        def tool_name(t):
            return getattr(
                t, "name", getattr(getattr(t, "function", None), "name", "unknown")
            )

        tool_names = [tool_name(t) for t in tools]
        print(
            f"🧰 Tools available: {', '.join(tool_names) if tool_names else '(none found)'}\n"
        )

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
