import subprocess
import json


def test_mcp_server_handshake():
    """
    Integration test to verify that the MCP server starts correctly,
    responds to a JSON-RPC initialize handshake over stdio, and terminates cleanly.
    """
    # Start the MCP server process
    process = subprocess.Popen(
        ["opsyield-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Construct the initialize request (MCP handshake)
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",  # FastMCP uses this or similar
                "capabilities": {},
                "clientInfo": {"name": "integration-test-client", "version": "1.0.0"},
            },
        }

        # Send request
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()

        # Read response
        response_line = process.stdout.readline()
        assert (
            response_line.strip()
        ), "Server did not return a response before terminating."

        # Parse response
        response = json.loads(response_line)

        # Assertions
        assert response.get("jsonrpc") == "2.0"
        assert response.get("id") == 1
        assert "result" in response
        assert "protocolVersion" in response["result"]

    finally:
        # Terminate cleanly
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
