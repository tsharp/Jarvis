"""
System-Addons MCP Server — Entry Point
═══════════════════════════════════════
FastMCP server für TRIONs dynamisches Selbstwissen (Artifact Registry).
Port: 8090
"""

import logging
import os
from fastmcp import FastMCP
from .tools import register_tools

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main():
    print("\n" + "=" * 50)
    print("SYSTEM-ADDONS MCP SERVER — START")
    print("=" * 50)

    print("→ Creating MCP server…")
    mcp = FastMCP("system_addons")
    print("✓ MCP instance active")

    print("→ Registering tools…")
    register_tools(mcp)
    print("✓ Tools loaded")

    try:
        tool_names = [t.name for t in mcp.tools]
        print(f"\nAvailable Tools ({len(tool_names)}):")
        for name in tool_names:
            print(f"   • {name}")
    except Exception:
        pass

    print("\n" + "=" * 50)
    print("SERVER READY — Listening on :8090 (streamable-http)")
    print("=" * 50 + "\n")

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8090,
        path="/mcp",
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
