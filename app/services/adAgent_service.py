from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.settings import Settings, get_settings
from app.mcp.server import get_ads_by_keyword
from app.models.chat import ChatMessage
import logging

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    """You are an helpful assistant that have access to getting ads for user. Analyze conversation history. "
    "If purchase intent is found, query ads. "
    "Return ONLY the ad text or 'NO_AD'."
    ### Semantic Search Guidelines
    When using the `get_ads_semantic` tool, you must transform the user's request into a "Sales Intent" string. 
    **Rules for Sales Intent:**
    1. **Focus on Nouns and Adjectives:** Use specific product categories and features (e.g., "Organic leather boots" instead of "I want to buy some nice shoes").
    2. **Remove Conversational Filler:** Strip away phrases like "I'm looking for," "Do you have," or "I would like."
    3. **Include Context:** If the user mentions a specific problem, include the solution category (e.g., "CRM software for small business lead tracking").
    4. **Structure:** Combine [Product Category] + [Key Features/Benefits] + [Target Audience]."""
)


class AdAgentService:
    def __init__(self, *, settings: Settings | None = None):
        self._settings = settings or get_settings()

        if not self._settings.gemini_api_key:
            raise RuntimeError(
                "Gemini API key is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY."
            )

        self.llm = ChatGoogleGenerativeAI(
            model=self._settings.gemini_model,
            temperature=0.1,
            api_key=self._settings.gemini_api_key,
        )
        self.tools = [get_ads_by_keyword]

        # Note: langchain.agents.create_agent does not accept a PromptTemplate;
        # it accepts a `system_prompt` which will be prepended as a SystemMessage.
        self.agent = create_agent(self.llm, self.tools, system_prompt=SYSTEM_PROMPT)

    @staticmethod
    def _to_lc_messages(history: list[ChatMessage] | list[BaseMessage]) -> list[BaseMessage]:
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
        self, history: list[ChatMessage] | list[BaseMessage], latest_message: str
    ) -> str | None:
        """
        Returns the ad text string if found, or None.
        Does NOT handle sending the message to the user.
        """
        try:
            lc_history = self._to_lc_messages(history)
            messages: list[BaseMessage] = [*lc_history, HumanMessage(content=latest_message)]
            result = await self.agent.ainvoke({"messages": messages})

            print("----------Ad Agent Result--------------")
            print("Ad Agent Result:", result)
            logger.info("Ad Agent Result: %s", result)
            result_messages = result.get("messages", []) if isinstance(result, dict) else []
            output = ""
            for msg in reversed(result_messages):
                if isinstance(msg, AIMessage):
                    candidate = self._content_to_text(getattr(msg, "content", None)).strip()
                    if candidate:
                        output = candidate
                        break
                if isinstance(msg, dict):
                    role = (msg.get("role") or "").lower()
                    if role in {"assistant", "ai"}:
                        candidate = self._content_to_text(msg.get("content")).strip()
                        if candidate:
                            output = candidate
                            break

            cleaned = output.strip().strip('"\'')
            if not cleaned:
                return None
            return None if cleaned.upper() == "NO_AD" else cleaned
        except Exception as e:
            logger.exception(
                "AdAgentService failed while analyzing and fetching ad"
            )
            raise e
