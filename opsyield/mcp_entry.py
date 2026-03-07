"""
OpsYield MCP Entrypoint
Only responsible for starting the MCP stdio server.
"""

from opsyield.core.config import validate_environment
from opsyield.mcp_stdio import mcp

def main():
    """
    Validate environment and run the MCP server using stdio transport.
    """
    validate_environment()
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
