from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestData(BaseModel):
    text: str

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "mistral"  # you can switch to "llama3" if installed

@app.post("/ask")
async def ask(data: RequestData):
    user_text = (data.text or "").strip()
    print("USER:", user_text)

    if not user_text:
        return {"reply": "Please say something."}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": f"""
You are a smart voice assistant.
Answer naturally in 1–2 short sentences.

User: {user_text}
Assistant:
""",
                    "stream": False,
                    "options": {
                        "temperature": 0.4,
                        "num_predict": 80
                    }
                }
            )

        # 🔍 debug (kept, but harmless)
        print("STATUS:", res.status_code)
        print("RAW:", res.text[:200])

        data_json = res.json()
        raw = data_json.get("response", "") or ""

        # 🔧 clean lightly (don’t over-cut)
        reply = raw.replace("Assistant:", "").replace("\n", " ").strip()

        # trim length for speech, but keep meaning
        if len(reply) > 140:
            reply = reply[:140].rsplit(" ", 1)[0]

        if not reply:
            reply = "I’m not sure, try again."

    except Exception as e:
        print("AI ERROR:", e)
        reply = "AI is not responding."

    return {"reply": reply}


@app.get("/")
def home():
    return {"status": "AI server running"}