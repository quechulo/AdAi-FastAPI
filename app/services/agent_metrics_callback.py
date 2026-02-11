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

        # Extract token usage from LLM response metadata
        # Google Gemini returns usage_metadata with total_token_count
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("usage_metadata", {})
            if isinstance(usage, dict):
                tokens = usage.get("total_token_count", 0)
                if tokens:
                    self.total_tokens += tokens
                    logger.debug(
                        f"LLM call completed: {tokens} tokens, "
                        f"cumulative: {self.total_tokens}"
                    )

        # Alternative: check in generations metadata
        if hasattr(response, "generations") and response.generations:
            for generation_list in response.generations:
                for generation in generation_list:
                    if hasattr(generation, "generation_info"):
                        gen_info = generation.generation_info or {}
                        usage = gen_info.get("usage_metadata", {})
                        if isinstance(usage, dict):
                            tokens = usage.get("total_token_count", 0)
                            if tokens:
                                self.total_tokens += tokens
                                break

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
