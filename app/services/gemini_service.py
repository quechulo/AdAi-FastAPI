import google.generativeai as genai
from app.config import settings
from app.schemas import ChatMessage

# Configure the SDK once
genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def generate_chat_response(self, message: str, history: list[ChatMessage]):
        # 1. Convert Pydantic schemas to Google's expected format
        # Google expects: [{'role': 'user', 'parts': ['text']}, ...]
        formatted_history = [
            {"role": msg.role, "parts": [msg.content]} 
            for msg in history
        ]

        # 2. Start a chat session with history
        chat_session = self.model.start_chat(history=formatted_history)

        # 3. Send the new message
        response = chat_session.send_message(message)
        
        return response.text