# mcp_servers/stdio_server.py
from mcp.server.fastmcp import FastMCP
import sys

mcp = FastMCP("weather-server")

@mcp.tool()
def get_weather(location: str) -> dict[str, str]:
    """Return fake weather data for a location."""
    return {"location": location, "temperature": "22°C", "summary": "Sunny"}

if __name__ == "__main__":
    if "--sse" in sys.argv:
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
