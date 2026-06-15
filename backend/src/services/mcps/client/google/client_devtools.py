# src/mcps/client/google/client_devtools.py
import os
import sys
import asyncio
import concurrent.futures
from typing import List
from contextlib import AsyncExitStack
from langchain_core.tools import StructuredTool
from pydantic import create_model, Field
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

class DevToolsMCPClient:
    """
    Cliente MCP Oficial de Google Chrome DevTools.
    Permite a Koda interactuar, depurar y leer la consola de Chrome.
    """
    def __init__(self):
        is_windows = sys.platform == "win32"
        command = "npx.cmd" if is_windows else "npx"

        args = ["-y", "chrome-devtools-mcp@latest"]
        
        # Si tienes Chrome abierto en modo debug (ej: http://127.0.0.1:9222), se conecta a ese.
        debug_url = os.getenv("CHROME_DEBUG_URL") 
        if debug_url:
            args.append(f"--browser-url={debug_url}")

        self.server_params = StdioServerParameters(
            command=command,
            args=args,
            env=os.environ.copy()
        )
        self._exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None

    def _run_sync(self, coro):
        def _thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_thread).result()

    def _mcp_schema_to_pydantic(self, name: str, schema: dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        fields = {}
        for key, prop in properties.items():
            prop_type = prop.get("type", "string")
            py_type = str
            if prop_type == "integer": py_type = int
            elif prop_type == "number": py_type = float
            elif prop_type == "boolean": py_type = bool
            elif prop_type == "array": py_type = list
            
            desc = prop.get("description", "")
            if key in required:
                fields[key] = (py_type, Field(..., description=desc))
            else:
                fields[key] = (py_type, Field(None, description=desc))
        
        class_name = "".join(word.capitalize() for word in name.split("-")) + "Schema"
        return create_model(class_name, **fields)

    async def __aenter__(self):
        try:
            read, write = await self._exit_stack.enter_async_context(stdio_client(self.server_params))
            self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            await self.session.initialize()
            return self
        except Exception as e:
            print(f"Error iniciando Chrome DevTools MCP: {e}")
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._exit_stack.aclose()
        self.session = None

    async def _call_server(self, name: str, kwargs: dict) -> str:
        try:
            if self.session:
                result = await self.session.call_tool(name, arguments=kwargs)
                texts = [c.text for c in result.content if c.type == "text"]
                return "\n".join(texts)
            
            async with AsyncExitStack() as stack:
                read, write = await stack.enter_async_context(stdio_client(self.server_params))
                temp_session = await stack.enter_async_context(ClientSession(read, write))
                await temp_session.initialize()
                
                result = await temp_session.call_tool(name, arguments=kwargs)
                texts = [c.text for c in result.content if c.type == "text"]
                return "\n".join(texts)
        except Exception as e:
            return f"Error interno en Chrome DevTools al ejecutar {name}: {str(e)}"

    async def get_langchain_tools(self) -> List[StructuredTool]:
        if not self.session:
            return []
        try:
            mcp_tools_response = await self.session.list_tools()
            langchain_tools = []
            for mcp_tool in mcp_tools_response.tools:
                tool_name = mcp_tool.name 
                dynamic_schema = self._mcp_schema_to_pydantic(tool_name, mcp_tool.inputSchema)
                
                def make_tools(t_name):
                    async def tool_func_async(**kwargs) -> str:
                        return await self._call_server(t_name, kwargs)
                    def tool_func_sync(**kwargs) -> str:
                        return self._run_sync(tool_func_async(**kwargs))
                    return tool_func_sync, tool_func_async
                
                sync_func, async_func = make_tools(tool_name)

                langchain_tools.append(
                    StructuredTool.from_function(
                        func=sync_func,           
                        coroutine=async_func,     
                        name=f"devtools_{tool_name.replace('-', '_')}",
                        description=mcp_tool.description,
                        args_schema=dynamic_schema 
                    )
                )
            return langchain_tools
        except Exception as e:
            print(f"Error extrayendo tools de Chrome DevTools: {e}")
            return []