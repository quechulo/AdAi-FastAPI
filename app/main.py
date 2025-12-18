from fastapi import FastAPI
from app.routers import chat

app = FastAPI(title="Thesis Agent Backend")

# Register the router
app.include_router(chat.router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "running", "service": "Conversational Ad AI"}