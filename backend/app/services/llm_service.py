"""LLM service wrapper for Claude API calls."""

import json
from typing import Any, Optional
from anthropic import Anthropic, AsyncAnthropic
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service for interacting with Claude API."""

    def __init__(self):
        """Initialize Anthropic client."""
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.model_haiku = settings.anthropic_model_haiku

    async def execute_structured(
        self,
        prompt: str,
        system_prompt: str = "",
        response_format: str = "json",
        temperature: float = 0.0,
        use_haiku: bool = False
    ) -> Any:
        """
        Execute a structured prompt and return parsed result.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            response_format: "json" or "text"
            temperature: Model temperature
            use_haiku: Use Haiku model for simpler tasks

        Returns:
            Parsed JSON or text response
        """

        model = self.model_haiku if use_haiku else self.model

        try:
            messages = [{"role": "user", "content": prompt}]

            response = await self.client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                messages=messages
            )

            content = response.content[0].text

            # Parse JSON if requested
            if response_format == "json":
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error("json_parse_failed", error=str(e), content=content[:500])
                    # Try to extract JSON from markdown code blocks
                    if "```json" in content:
                        json_start = content.find("```json") + 7
                        json_end = content.find("```", json_start)
                        json_str = content[json_start:json_end].strip()
                        return json.loads(json_str)
                    raise

            return content

        except Exception as e:
            logger.error("llm_execution_failed", error=str(e))
            raise

    async def execute_long_form(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3
    ) -> str:
        """
        Execute a long-form generation (like report writing).

        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Slightly higher for more natural writing

        Returns:
            Generated text
        """

        try:
            messages = [{"role": "user", "content": prompt}]

            response = await self.client.messages.create(
                model=self.model,  # Use full Sonnet for quality
                max_tokens=8192,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                messages=messages
            )

            return response.content[0].text

        except Exception as e:
            logger.error("llm_long_form_failed", error=str(e))
            raise

    async def execute_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        max_iterations: int = 5,
        system_prompt: str = ""
    ) -> Any:
        """
        Execute with tool calling support (for subagents).

        Args:
            prompt: User prompt
            tools: List of tool definitions
            max_iterations: Max tool call iterations
            system_prompt: System prompt

        Returns:
            Final result after tool interactions
        """

        try:
            messages = [{"role": "user", "content": prompt}]

            for iteration in range(max_iterations):
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt if system_prompt else None,
                    messages=messages,
                    tools=tools
                )

                # Check if model wants to use tools
                if response.stop_reason == "tool_use":
                    # Extract tool calls
                    tool_uses = [
                        block for block in response.content
                        if block.type == "tool_use"
                    ]

                    # Add assistant message
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Execute tools and add results
                    tool_results = []
                    for tool_use in tool_uses:
                        result = await self._execute_tool(
                            tool_use.name,
                            tool_use.input
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result)
                        })

                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })

                else:
                    # No more tool calls, return final response
                    return response.content[0].text

            # Max iterations reached
            logger.warning("max_tool_iterations_reached")
            return "Maximum tool iterations reached. Partial result returned."

        except Exception as e:
            logger.error("llm_tool_execution_failed", error=str(e))
            raise

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """
        Execute a tool call.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters

        Returns:
            Tool execution result
        """

        from app.agents.tools import ToolExecutor

        executor = ToolExecutor()
        return await executor.execute(tool_name, tool_input)
