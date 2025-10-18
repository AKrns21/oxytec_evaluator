"""LLM service wrapper for Claude API calls."""

import json
import os
from typing import Any, Optional
from anthropic import Anthropic, AsyncAnthropic
from openai import AsyncOpenAI
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Configure LangSmith tracing if enabled
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    if settings.langchain_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
    logger.info("langsmith_tracing_enabled",
                project=settings.langchain_project,
                endpoint=settings.langchain_endpoint or "default")


class LLMService:
    """Service for interacting with Claude API."""

    def __init__(self):
        """Initialize Anthropic and OpenAI clients with LangSmith tracing."""
        # Create base clients
        base_anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        base_openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Wrap with LangSmith if tracing is enabled
        if settings.langchain_tracing_v2 and settings.langchain_api_key:
            try:
                from langsmith.wrappers import wrap_anthropic, wrap_openai
                self.client = wrap_anthropic(base_anthropic_client)
                self.openai_client = wrap_openai(base_openai_client)
                logger.info("langsmith_wrappers_applied")
            except ImportError:
                logger.warning("langsmith_wrappers_not_available",
                             message="Install langsmith package to enable tracing")
                self.client = base_anthropic_client
                self.openai_client = base_openai_client
        else:
            self.client = base_anthropic_client
            self.openai_client = base_openai_client

        self.model = settings.anthropic_model
        self.model_haiku = settings.anthropic_model_haiku

    async def execute_structured(
        self,
        prompt: str,
        system_prompt: str = "",
        response_format: str = "json",
        temperature: float = 0.0,
        use_haiku: bool = False,
        use_extended_thinking: bool = False,
        use_openai: bool = False,
        openai_model: str = None
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

        # Use OpenAI for extraction if requested
        if use_openai:
            return await self._execute_openai_structured(
                prompt, system_prompt, response_format, temperature, openai_model
            )

        model = self.model_haiku if use_haiku else self.model

        try:
            # Don't use prefill - it breaks markdown cleanup
            messages = [{"role": "user", "content": prompt}]

            # Build kwargs, only include system if provided
            kwargs = {
                "model": model,
                "max_tokens": 4096,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            # Enable extended thinking if requested
            if use_extended_thinking:
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": 2000
                }
                # Extended thinking requires temperature=1.0
                kwargs["temperature"] = 1.0

            response = await self.client.messages.create(**kwargs)

            # Simple content extraction - just get the text
            content = response.content[0].text

            # Parse JSON if requested
            if response_format == "json":
                # Strip whitespace
                content = content.strip()

                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content[7:]  # Remove ```json
                elif content.startswith("```"):
                    content = content[3:]  # Remove ```

                if content.endswith("```"):
                    content = content[:-3]  # Remove trailing ```

                content = content.strip()

                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error("json_parse_failed",
                               error=str(e),
                               content_length=len(content),
                               content_preview=content[:500])
                    raise

            return content

        except Exception as e:
            logger.error("llm_execution_failed", error=str(e))
            raise

    async def execute_long_form(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        model: str = None
    ) -> str:
        """
        Execute a long-form generation (like report writing).

        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Slightly higher for more natural writing
            model: Optional model override

        Returns:
            Generated text
        """

        try:
            messages = [{"role": "user", "content": prompt}]

            # Build kwargs, only include system if provided
            kwargs = {
                "model": model or self.model,
                "max_tokens": 8192,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = await self.client.messages.create(**kwargs)

            return response.content[0].text

        except Exception as e:
            logger.error("llm_long_form_failed", error=str(e))
            raise

    async def execute_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        max_iterations: int = 5,
        system_prompt: str = "",
        temperature: float = 0.0,
        model: str = None,
        use_openai: bool = False,
        openai_model: str = None
    ) -> Any:
        """
        Execute with tool calling support (for subagents).

        Args:
            prompt: User prompt
            tools: List of tool definitions
            max_iterations: Max tool call iterations
            system_prompt: System prompt
            temperature: Model temperature
            model: Optional Claude model override
            use_openai: Use OpenAI instead of Claude
            openai_model: Optional OpenAI model override

        Returns:
            Final result after tool interactions
        """

        # If use_openai is True, delegate to OpenAI structured execution
        # (Note: OpenAI tool calling format is different, so for now we just use structured output)
        if use_openai:
            return await self.execute_structured(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="text",
                temperature=temperature,
                use_openai=True,
                openai_model=openai_model
            )

        try:
            messages = [{"role": "user", "content": prompt}]

            for iteration in range(max_iterations):
                # Build kwargs, only include system if provided
                kwargs = {
                    "model": model or self.model,
                    "max_tokens": 4096,
                    "temperature": temperature,
                    "messages": messages,
                    "tools": tools
                }

                if system_prompt:
                    kwargs["system"] = system_prompt

                response = await self.client.messages.create(**kwargs)

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

    async def _execute_openai_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_format: str,
        temperature: float,
        openai_model: str = None
    ) -> Any:
        """Execute structured output with OpenAI (better JSON handling)."""
        try:
            messages = [{"role": "user", "content": prompt}]
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})

            # Use specified model or fallback to gpt-4o
            model = openai_model or "gpt-4o"

            # Use configured OpenAI model (gpt-5, gpt-5-mini, gpt-5-nano, etc.) with JSON mode
            # GPT-5 models don't support temperature, they use reasoning_effort instead
            create_params = {
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"} if response_format == "json" else {"type": "text"}
            }

            # Only add temperature for non-GPT-5 models
            if not model.startswith("gpt-5"):
                create_params["temperature"] = temperature
            else:
                # Map temperature to reasoning_effort for GPT-5 models
                # Low temp (0.0-0.3) -> minimal, Medium (0.4-0.7) -> low, High (0.8-1.0) -> medium
                if temperature <= 0.3:
                    create_params["reasoning_effort"] = "minimal"
                elif temperature <= 0.7:
                    create_params["reasoning_effort"] = "low"
                else:
                    create_params["reasoning_effort"] = "medium"

            response = await self.openai_client.chat.completions.create(**create_params)

            content = response.choices[0].message.content

            if response_format == "json":
                return json.loads(content)
            return content

        except Exception as e:
            logger.error("openai_execution_failed", error=str(e))
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
