import os
import json
import uvicorn
import contextlib

from interfaces import (
    rag_finance_report_search,
    get_finance_report_filters
)

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type


from mcp import types as mcp_types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from collections.abc import AsyncIterator

from infrastructure.logging_config import logger

logger.info("Creating MCP Server instance...")
app = Server("Servidor-mcp")

ADK_TOOLS = {
    "rag_finance_report_search": FunctionTool(func=rag_finance_report_search),
    "get_finance_report_filters": FunctionTool(func=get_finance_report_filters),
}


@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler to list tools this server exposes."""
    logger.info("MCP Server: Received list_tools request.")
    mcp_tools_list = []
    for tool_name, adk_tool_instance in ADK_TOOLS.items():
        if not adk_tool_instance.name:
            adk_tool_instance.name = tool_name

        mcp_tool_schema = adk_to_mcp_tool_type(adk_tool_instance)
        logger.info(
            f"MCP Server: Advertising tool: {mcp_tool_schema.name}, InputSchema: {mcp_tool_schema.inputSchema}"
        )
        mcp_tools_list.append(mcp_tool_schema)
    return mcp_tools_list


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    """MCP handler to execute a tool call requested by an MCP client."""
    logger.info(f"MCP Server: Received call_tool request for '{name}' with args: {arguments}")

    adk_tool_instance = ADK_TOOLS.get(name)

    if not adk_tool_instance:
        logger.warning(f"MCP Server: Tool '{name}' not found/exposed by this server.")
        error_payload = {
            "success": False,
            "message": f"Tool '{name}' not implemented by this server.",
        }
        return [
            mcp_types.TextContent(
                type="text",
                text=json.dumps(error_payload)
            )
        ]

    try:
        adk_tool_response = await adk_tool_instance.run_async(
            args=arguments,
            tool_context=None,  # type: ignore
        )

        logger.info(f"MCP Server: ADK tool '{name}' executed. Response: {adk_tool_response}")

        return [
            mcp_types.TextContent(
                type="text",
                text=json.dumps(adk_tool_response, indent=2)
            )
        ]

    except Exception as e:
        logger.error(
            f"MCP Server: Error executing ADK tool '{name}': {e}",
            exc_info=True
        )

        error_payload = {
            "success": False,
            "message": f"Failed to execute tool '{name}': {str(e)}",
        }

        return [
            mcp_types.TextContent(
                type="text",
                text=json.dumps(error_payload)
            )
        ]


# 🔁 Session manager for Streamable HTTP
session_manager: StreamableHTTPSessionManager = StreamableHTTPSessionManager(
    app=app,
    event_store=None,
    stateless=True,
)

# 🔁 Lifespan for the session manager
@contextlib.asynccontextmanager
async def lifespan(_: Starlette) -> AsyncIterator[None]:
    logger.info("MCP Server: Starting session manager...")
    async with session_manager.run():
        try:
            yield
        finally:
            logger.info("MCP Server: Session manager shutting down.")

# 🔧 Final Starlette app
mcp_http_app = Starlette(
    debug=False,
    routes=[
        Mount("/mcp", app=session_manager.handle_request),
    ],
    lifespan=lifespan,
)


def start_http_server():
    try:
        host = "0.0.0.0"
        port = 8001

        logger.info(f"Starting MCP HTTP server on http://{host}:{port}/mcp ...")
        uvicorn.run(mcp_http_app, host=host, port=port)

    except KeyboardInterrupt:
        logger.info("MCP HTTP Server stopped by user.")
    except Exception as e:
        logger.critical(f"MCP HTTP Server failed: {e}", exc_info=True)


if __name__ == "__main__":
    start_http_server()
