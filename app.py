from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from slack_sdk import WebClient
import os
import requests
import fitz  # PyMuPDF
from io import BytesIO
import uvicorn
from typing import Optional, Dict, Any, List

app = FastAPI()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

def gen_pdf(url):
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        with fitz.open(stream=BytesIO(response.content), filetype="pdf") as doc:
            text = "\n".join(page.get_text() for page in doc)
            print("추출:\n", text[:100])
    except requests.HTTPError as e:
        print(f"실패: {e}")

class SlackFile(BaseModel):
    mimetype: Optional[str] = None
    url_private_download: Optional[str] = None

class SlackEventInner(BaseModel):
    type: str
    channel: Optional[str] = None
    text: Optional[str] = None
    files: Optional[List[SlackFile]] = None

class SlackEvent(BaseModel):
    type: str
    challenge: Optional[str] = None
    event: Optional[SlackEventInner] = None

@app.post("/slack/events")
async def slack_events(payload: SlackEvent):
    print(f'data.get("type"): {payload.type}, ')

    if payload.type == "url_verification":
        return PlainTextResponse(content=payload.challenge)

    if payload.type == "event_callback" and payload.event:
        event = payload.event
        print("Received event:", event)

        if event.type == "app_mention":
            files = event.files or []
            for f in files:
                if f.mimetype == "application/pdf" and f.url_private_download:
                    gen_pdf(f.url_private_download)

            if event.channel and event.text:
                slack_client.chat_postMessage(channel=event.channel, text=event.text)

        return PlainTextResponse("")

    return PlainTextResponse("Ignored")

@app.post("/")
async def index():
    
    return PlainTextResponse("")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=3000, reload=True)
