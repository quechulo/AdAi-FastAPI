# app/services/mcp_service.py
from __future__ import annotations

import asyncio
import json
import logging
import time

from google import genai
from google.genai import types

from app.core.settings import Settings, get_settings
from app.models.chat import ChatMessage
# We import the mcp_client interface, but we will likely inject the server direct connection
from app.services.mcp_client import McpClient 

logger = logging.getLogger(__name__)


class McpService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        mcp_client: McpClient,
        system_prompt: str | None = None,
    ):
        self._settings = settings or get_settings()
        self._mcp = mcp_client
        self._system_prompt = (
            system_prompt
            if system_prompt is not None
            else getattr(self._settings, "mcp_system_prompt", None)
        )
        self._client = genai.Client(api_key=self._settings.gemini_api_key)

    @staticmethod
    def _extract_total_tokens(usage: object) -> int:
        return (
            getattr(usage, "total_token_count", None)
            or getattr(usage, "total_tokens", 0)
            or 0
        )

    async def answer(
        self,
        *,
        message: str,
        history: list[ChatMessage],
        max_tool_steps: int = 6,
    ) -> tuple[str, float, int, dict[str, float | int]]:

        start_time = time.perf_counter()
        total_tokens = 0
        embedding_tokens = 0
        llm_call_count = 0
        tool_call_count = 0

        # 1. Prepare Initial Chat History
        contents: list[types.Content] = []
        for msg in history:
            role = "model" if msg.role == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=part) for part in msg.parts]))

        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

        try:
            # Connect to MCP Session
            async with self._mcp.session() as mcp_session:

                # 2. Discover Tools
                tools_result = await mcp_session.list_tools()
                gemini_tools = []

                for t in getattr(tools_result, "tools", []):
                    gemini_tools.append(types.FunctionDeclaration(
                        name=t.name,
                        description=t.description,
                        parameters=t.inputSchema or {"type": "object", "properties": {}}
                    ))

                tool_config = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="AUTO"
                    )
                )

                # 3. Execution Loop
                for i in range(max_tool_steps):
                    # Generate Content
                    response = await asyncio.to_thread(
                        self._client.models.generate_content,
                        model=self._settings.gemini_model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=self._system_prompt,
                            tools=[types.Tool(function_declarations=gemini_tools)],
                            tool_config=tool_config,
                        )
                    )
                    llm_call_count += 1

                    # Accumulate token usage across all loop iterations (including tool calls).
                    # google-genai SDK returns usage_metadata.total_token_count on the response.
                    usage = getattr(response, "usage_metadata", None)
                    if usage is not None:
                        call_tokens = self._extract_total_tokens(usage)
                        total_tokens += call_tokens
                        logger.debug(f"MCP step {i + 1}: {call_tokens} tokens, cumulative: {total_tokens}")
                    else:
                        logger.warning(f"MCP step {i + 1}: usage_metadata is None, token count unavailable")

                    # Inspect Response
                    cand = response.candidates[0]
                    # Append the model's thought process/tool calls to history
                    contents.append(cand.content)

                    # Extract Function Calls
                    function_calls = [
                        part.function_call for part in cand.content.parts
                        if part.function_call is not None
                    ]

                    # If no function calls, return text
                    if not function_calls:
                        text_parts = [p.text for p in cand.content.parts if p.text]
                        final_text = " ".join(text_parts) if text_parts else "No response generated."
                        elapsed = time.perf_counter() - start_time
                        breakdown: dict[str, float | int] = {
                            "llm_call_count": llm_call_count,
                            "tool_call_count": tool_call_count,
                        }
                        logger.info(f"MCP chat completed: {i + 1} LLM call(s), {total_tokens} tokens, {elapsed:.3f}s")
                        return (final_text, elapsed, total_tokens, breakdown)

                    # Execute Tools
                    parts_response = []
                    for call in function_calls:
                        tool_call_count += 1
                        logger.info(f"Step {i+1}: Calling tool {call.name}")
                        print(f"Step {i+1}: Calling tool {call.name} with args {call.args}")

                        try:
                            # Call the tool via MCP
                            result = await mcp_session.call_tool(call.name, arguments=call.args)
                            print(f"Tool {call.name} returned result: {result}")
                            # Parse result content (MCP returns a list of text/image content)
                            # We flatten it to a single string for the LLM
                            content_text = ""
                            if hasattr(result, 'content') and isinstance(result.content, list):
                                for item in result.content:
                                    item_text = getattr(item, "text", None)
                                    if not isinstance(item_text, str):
                                        continue
                                    try:
                                        payload = json.loads(item_text)
                                    except json.JSONDecodeError:
                                        continue
                                    if isinstance(payload, dict):
                                        embed_tokens = int(payload.get("embedding_tokens", 0) or 0)
                                        if embed_tokens:
                                            embedding_tokens += embed_tokens
                                            total_tokens += embed_tokens
                                content_text = "\n".join([c.text for c in result.content if hasattr(c, 'text')])
                            else:
                                content_text = str(result)

                            # Create the function response part
                            parts_response.append(types.Part.from_function_response(
                                name=call.name,
                                response={"result": content_text}
                            ))
                        except Exception as e:
                            logger.error(f"Tool error: {e}")
                            parts_response.append(types.Part.from_function_response(
                                name=call.name,
                                response={"error": str(e)}
                            ))

                    contents.append(types.Content(role="user", parts=parts_response))

                elapsed = time.perf_counter() - start_time
                breakdown: dict[str, float | int] = {
                    "llm_call_count": llm_call_count,
                    "tool_call_count": tool_call_count,
                    "embedding_tokens": embedding_tokens,
                }
                return (
                    "Max tool steps reached. I could not find a final answer.",
                    elapsed,
                    total_tokens,
                    breakdown,
                )

        except Exception as e:
            logger.exception("Error in McpService")
            elapsed = time.perf_counter() - start_time
            breakdown: dict[str, float | int] = {
                "llm_call_count": llm_call_count,
                "tool_call_count": tool_call_count,
                "embedding_tokens": embedding_tokens,
            }
            return (f"System Error: {str(e)}", elapsed, total_tokens, breakdown)
