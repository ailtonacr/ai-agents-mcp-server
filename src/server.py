import json
import uvicorn
import contextlib

from interfaces import (
    rag_finance_report_search,
    get_finance_report_filters
)

from utils.mcp_function_tool import MCPFunctionTool

from mcp import types as mcp_types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from collections.abc import AsyncIterator

from infrastructure.logging_config import logger

logger.info("Creating MCP Server instance...")
app = Server("Servidor-mcp")

MCP_TOOLS = {
    "rag_finance_report_search": MCPFunctionTool(
        func=rag_finance_report_search,
        description="Searches the ACR Tech finance RAG system for reports based on a query and filters."
    ),
    "get_finance_report_filters": MCPFunctionTool(
        func=get_finance_report_filters,
        description="Returns a list of all available filters and values for the finance RAG system."
    )
}


@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler to list tools this server exposes."""
    logger.info("MCP Server: Received list_tools request.")
    mcp_tools_list = []

    for tool_name, mcp_tool_instance in MCP_TOOLS.items():
        if not mcp_tool_instance.name:
            mcp_tool_instance.name = tool_name

        mcp_tool_schema = mcp_tool_instance.to_mcp_tool()
        logger.info(
            f"MCP Server: Advertising tool: {mcp_tool_schema.name}, InputSchema: {mcp_tool_schema.inputSchema}"
        )
        mcp_tools_list.append(mcp_tool_schema)
    return mcp_tools_list


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    """MCP handler to execute a tool call requested by an MCP client."""
    logger.info(f"MCP Server: Received call_tool request for '{name}' with args: {arguments}")

    mcp_tool_instance = MCP_TOOLS.get(name)

    if not mcp_tool_instance:
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
        mcp_tool_response = await mcp_tool_instance.run_async(args=arguments)

        logger.info(f"MCP Server: MCP tool '{name}' executed. Response: {mcp_tool_response}")

        return [
            mcp_types.TextContent(
                type="text",
                text=mcp_tool_response
            )
        ]

    except Exception as e:
        logger.error(
            f"MCP Server: Error executing MCP tool '{name}': {e}",
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
