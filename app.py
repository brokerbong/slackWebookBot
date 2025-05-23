from fastapi import FastAPI, Request, Header
from fastapi.responses import PlainTextResponse
from slack_sdk import WebClient
import os
import requests
import fitz  # PyMuPDF
from io import BytesIO
import uvicorn

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
            print("\ud83d\udcc4 추출된 텍스트:\n", text[:300])
    except requests.HTTPError as e:
        print(f"\u274c 다운로드 실패: {e}")

@app.post("/slack/events")
async def slack_events(request: Request):
    data = await request.json()
    print(f'data.get("type"): {data.get("type")}, ')

    if data.get("type") == "url_verification":
        return PlainTextResponse(content=data.get("challenge"))

    if data.get("type") == "event_callback":
        event = data.get("event", {})
        print("Received event:", event)

        if event.get("type") == "app_mention":
            files = event.get("files", [])
            for f in files:
                if f.get("mimetype") == "application/pdf":
                    download_url = f.get("url_private_download")
                    gen_pdf(download_url)

            channel = event.get("channel")
            text = event.get("text")
            slack_client.chat_postMessage(channel=channel, text=text)

        return PlainTextResponse("")

    return PlainTextResponse("Ignored")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
