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
    "You are an Ad Director. Analyze conversation history. "
    "If purchase intent is found, query ads. "
    "Return ONLY the ad text or 'NO_AD'."
)

class AdAgentService:
    def __init__(self, *, settings: Settings | None = None):
        self._settings = settings or get_settings()

        if not self._settings.gemini_api_key:
            raise RuntimeError(
                "Gemini API key is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY."
            )

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            temperature=0,
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

            logger.exception("---------------------------------------")
            logger.exception("Ad Agent Result: %s", result)
            logger.exception("---------------------------------------")
            result_messages = result.get("messages", []) if isinstance(result, dict) else []
            output = ""
            for msg in reversed(result_messages):
                if isinstance(msg, AIMessage):
                    output = (msg.content or "").strip()
                    break
                if isinstance(msg, dict):
                    role = (msg.get("role") or "").lower()
                    if role in {"assistant", "ai"}:
                        output = (msg.get("content") or "").strip()
                        break

            cleaned = output.strip().strip('"\'')
            if not cleaned:
                return None
            return None if cleaned.upper() == "NO_AD" or "NO_AD" in cleaned.upper() else cleaned
        except Exception:
            logger.exception("AdAgentService failed while analyzing and fetching ad")
            return None