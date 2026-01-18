import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class McpClient:
    """
    Manages the connection to the local MCP server subprocess.
    """
    def __init__(self, server_script_path: str = "app/mcp/server.py"):
        # Determine the absolute path to the server script
        self.server_script_path = os.path.abspath(server_script_path)
        
        env = os.environ.copy()
        # 2. Add the current directory (Project Root) to PYTHONPATH
        # This allows the subprocess to perform imports like "from app.db..."
        env["PYTHONPATH"] = os.getcwd()

        # Define how we run the server (using the same python environment)
        self.server_params = StdioServerParameters(
            command=sys.executable,  # Uses the current python interpreter
            args=[self.server_script_path],
            env=env
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[ClientSession, None]:
        """
        Context manager that spawns the subprocess and establishes the session.
        Usage:
            async with client.session() as session:
                result = await session.call_tool(...)
        """
        # stdio_client handles the process spawning and cleanup
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                yield session

    @staticmethod
    def call_tool_result_to_dict(result: Any) -> dict:
        """Helper to serialize MCP tool results for the frontend/logs."""
        content_list = []
        # MCP tools return a list of text/image content objects
        if hasattr(result, "content") and isinstance(result.content, list):
            for item in result.content:
                if hasattr(item, "text"):
                    content_list.append({"type": "text", "text": item.text})
                elif hasattr(item, "data"):
                     content_list.append({"type": "image", "data": "..."}) # truncated for logs
        
        return {
            "content": content_list,
            "isError": getattr(result, "isError", False)
        }
