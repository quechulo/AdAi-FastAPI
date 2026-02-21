from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.settings import Settings, get_settings
from app.mcp.server import get_ads_by_keyword, get_ads_semantic
from app.models.chat import ChatMessage
from app.services.agent_metrics_callback import MetricsCallbackHandler
import logging

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    """You are a helpful assistant that helps users find relevant ads based on their needs.
    Analyze conversation history for purchase intent. If found, query ads using the appropriate tool.
    Return ONLY the ad text or 'NO_AD'.
    
    ### Tool Selection Guidelines
    
    **Use `get_ads_by_keyword` when:**
    - User mentions specific product categories, product names, brands, or models (e.g., "iphone", "Nike shoes")
    - User mentions some category of experience, hobby, plans, general intent (e.g., "workout", "camping", "clothing")
    - Query is 1-2 words or short phrases
    - User asks for exact/specific items
    - Examples: "investment", "wireless headphones", "running shoes"
    
    **Use `get_ads_semantic` when:**
    - User describes needs, requirements, or problems (not specific products)
    - Query contains multiple attributes or requirements
    - User provides descriptive context (5+ words)
    - Examples: "laptop for gaming", "headphones for noisy commute", "shoes for flat feet with good arch support"
    
    ### How to Use get_ads_semantic
    
    Transform the user's request into a clean search query:
    
    **Rules:**
    1. **Focus on Nouns and Adjectives:** Use specific product categories and features
       (e.g., "Organic leather boots" NOT "I want to buy some nice shoes")
    2. **Remove Conversational Filler:** Strip "I'm looking for", "Do you have", "I would like"
    3. **Include Context:** If user mentions a problem, include the solution category
       (e.g., "CRM software for small business lead tracking")
    4. **Structure:** Combine [Product Category] + [Key Features/Benefits] + [Target Audience]
    
    **Decision Priority:**
    - If query is 1-3 words → use keyword search (faster)
    - If query is descriptive/multi-attribute → use semantic search (better relevance)
    - When uncertain, prefer semantic search for better results"""
)


class AdAgentService:
    def __init__(self, *, settings: Settings | None = None):
        self._settings = settings or get_settings()

        if not self._settings.gemini_api_key:
            raise RuntimeError(
                """Gemini API key is not configured.
                Set GEMINI_API_KEY or GOOGLE_API_KEY."""
            )

        self.llm = ChatGoogleGenerativeAI(
            model=self._settings.gemini_model,
            temperature=0.1,
            api_key=self._settings.gemini_api_key,
        )
        self.tools = [get_ads_by_keyword, get_ads_semantic]

        # Note: langchain.agents.create_agent does not accept a PromptTemplate;
        # it accepts a `system_prompt`
        # which will be prepended as a SystemMessage.
        self.agent = create_agent(
            self.llm,
            self.tools,
            system_prompt=SYSTEM_PROMPT
        )

    @staticmethod
    def _to_lc_messages(
        history: list[ChatMessage] | list[BaseMessage]
    ) -> list[BaseMessage]:
        if not history:
            return []
        first = history[0]
        if isinstance(first, BaseMessage):
            return list(history)  # already in LangChain format

        lc_history: list[BaseMessage] = []
        for msg in history:  # type: ignore[assignment]
            role = getattr(msg, "role", None)
            content = str(getattr(msg, "parts", "") or "")
            if role in {"user", "human"}:
                lc_history.append(HumanMessage(content=content))
            else:
                # Treat everything else as assistant/model for safety.
                lc_history.append(AIMessage(content=content))
        return lc_history

    @staticmethod
    def _content_to_text(content: object) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            for key in ("text", "content", "value"):
                value = content.get(key)
                if isinstance(value, str):
                    return value
            return ""
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                text = AdAgentService._content_to_text(part)
                if text:
                    parts.append(text)
            return "\n".join(parts)
        return str(content)

    async def analyze_and_get_ad(
        self,
        history: list[ChatMessage] | list[BaseMessage],
        latest_message: str
    ) -> dict[str, Any]:
        """
        Analyzes conversation for purchase intent and retrieves relevant ads.

        Returns:
            dict with keys:
                - ad_text: str | None - The ad text if found, or None
                - generation_time: float - Time spent in LLM calls (seconds)
                - used_tokens: int - Total tokens consumed across all LLM calls
        """
        # Initialize metrics tracking callback
        metrics_callback = MetricsCallbackHandler()

        try:
            lc_history = self._to_lc_messages(history)
            messages: list[BaseMessage] = [
                *lc_history,
                HumanMessage(content=latest_message)
            ]

            # Execute agent with metrics tracking
            result = await self.agent.ainvoke(
                {"messages": messages},
                config={"callbacks": [metrics_callback]}
            )

            print("----------Ad Agent Result--------------")
            print("Ad Agent Result:", result)
            logger.info("Ad Agent Result: %s", result)
            result_messages = (
                result.get("messages", [])
                if isinstance(result, dict)
                else []
            )
            output = ""
            for msg in reversed(result_messages):
                if isinstance(msg, AIMessage):
                    candidate = self._content_to_text(
                        getattr(msg, "content", None)
                    ).strip()
                    if candidate:
                        output = candidate
                        break
                if isinstance(msg, dict):
                    role = (msg.get("role") or "").lower()
                    if role in {"assistant", "ai"}:
                        candidate = self._content_to_text(
                            msg.get("content")
                        ).strip()
                        if candidate:
                            output = candidate
                            break

            cleaned = output.strip().strip('"\'')
            ad_text = (
                None
                if (not cleaned or cleaned.upper() == "NO_AD")
                else cleaned
            )

            # Extract metrics from callback
            metrics = metrics_callback.get_metrics()

            logger.info(
                f"Ad agent completed: {metrics['llm_call_count']} LLM calls, "
                f"{metrics['total_tokens']} tokens, "
                f"{metrics['generation_time']:.3f}s"
            )

            return {
                "ad_text": ad_text,
                "generation_time": metrics["generation_time"],
                "used_tokens": metrics["total_tokens"],
            }
        except Exception:
            logger.exception(
                "AdAgentService failed while analyzing and fetching ad"
            )
            # Return metrics even on error
            metrics = metrics_callback.get_metrics()
            return {
                "ad_text": None,
                "generation_time": metrics["generation_time"],
                "used_tokens": metrics["total_tokens"],
            }
