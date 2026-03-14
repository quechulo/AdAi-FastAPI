"""LangChain callback handler for tracking LLM generation metrics.

This handler captures token usage and timing information from all LLM calls
made during agent execution, including planning, tool decisions, and synthesis.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


class MetricsCallbackHandler(BaseCallbackHandler):
    """Callback handler that tracks generation time and token usage
    across LLM calls.
    """

    def __init__(self):
        super().__init__()
        self.total_tokens = 0
        self.total_generation_time = 0.0
        self._call_start_times: dict[str, float] = {}
        self.llm_call_count = 0

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Capture the start time of an LLM call."""
        run_id = kwargs.get("run_id")
        if run_id:
            self._call_start_times[str(run_id)] = time.perf_counter()
            self.llm_call_count += 1

    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any,
    ) -> None:
        """Extract token usage and calculate generation time
        when LLM call completes.
        """
        run_id = kwargs.get("run_id")

        # Calculate generation time for this call
        if run_id and str(run_id) in self._call_start_times:
            start_time = self._call_start_times.pop(str(run_id))
            call_time = time.perf_counter() - start_time
            self.total_generation_time += call_time

        # Extract token usage from LLM response metadata.
        # langchain-google-genai stores usage in generation.message.usage_metadata
        # as a plain dict with keys: input_tokens, output_tokens, total_tokens.
        # We also check llm_output and generation_info as fallbacks for other models.
        def _extract_total_tokens(usage: Any) -> int:
            if isinstance(usage, dict):
                # Standard LangChain AIMessage format
                return usage.get("total_tokens") or usage.get("total_token_count", 0)
            # Protobuf UsageMetadata object
            return getattr(usage, "total_tokens", 0) or getattr(usage, "total_token_count", 0)

        tokens = 0

        # Primary: message.usage_metadata on ChatGeneration (langchain-google-genai)
        if not tokens and hasattr(response, "generations") and response.generations:
            for generation_list in response.generations:
                for generation in generation_list:
                    msg = getattr(generation, "message", None)
                    usage = getattr(msg, "usage_metadata", None) if msg is not None else None
                    if usage is not None:
                        tokens = _extract_total_tokens(usage)
                    if tokens:
                        break
                if tokens:
                    break

        # Fallback: llm_output (some model integrations)
        if not tokens and hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("usage_metadata")
            if usage is not None:
                tokens = _extract_total_tokens(usage)

        # Fallback: generation_info
        if not tokens and hasattr(response, "generations") and response.generations:
            for generation_list in response.generations:
                for generation in generation_list:
                    gen_info = getattr(generation, "generation_info", None) or {}
                    usage = gen_info.get("usage_metadata")
                    if usage is not None:
                        tokens = _extract_total_tokens(usage)
                    if tokens:
                        break
                if tokens:
                    break

        if tokens:
            self.total_tokens += tokens
            logger.debug(
                f"LLM call completed: {tokens} tokens, "
                f"cumulative: {self.total_tokens}"
            )

    def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Clean up timing data if LLM call fails."""
        run_id = kwargs.get("run_id")
        if run_id and str(run_id) in self._call_start_times:
            # Still count the time even if it errored
            start_time = self._call_start_times.pop(str(run_id))
            call_time = time.perf_counter() - start_time
            self.total_generation_time += call_time

        logger.warning(f"LLM call failed: {error}")

    def get_metrics(self) -> dict[str, Any]:
        """Return aggregated metrics from all LLM calls."""
        return {
            "total_tokens": self.total_tokens,
            "generation_time": self.total_generation_time,
            "llm_call_count": self.llm_call_count,
        }

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.total_tokens = 0
        self.total_generation_time = 0.0
        self._call_start_times.clear()
        self.llm_call_count = 0
