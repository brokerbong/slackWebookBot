from flask import Flask, request, jsonify
from slack_sdk import WebClient
import os
import requests
import fitz  # PyMuPDF
from io import BytesIO

app = Flask(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

def gen_pdf(url):
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # 오류 시 예외 발생

    # 3. 메모리에서 PyMuPDF로 PDF 열기
    pdf_stream = BytesIO(response.content)
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    
    # 4. 페이지별 텍스트 추출
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        print(f"[Page {page_num}]\n{text}\n{'-'*50}")

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()
    print(f'data.get("type"): {data.get("type")}, ')
    # Slack URL 인증용 응답
    if data.get("type") == "url_verification":
        return data.get("challenge"), 200, {"Content-Type": "text/plain"}

    # 일반 이벤트 처리
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        print("Received event:", event)
        
        if event.get("type") == "app_mention":
            if event.get("files"):
               for f in event["files"]:
                mimetype = f.get("mimetype", "")
                if mimetype == "application/pdf":
                    downloadUrl = f.get("url_private_download")
                    gen_pdf(downloadUrl)
            
            channel = event.get("channel")
            user = event.get("user")
            text = event.get("text")

            slack_client.chat_postMessage(channel=channel, text=text)
        
        return "", 200

    return "Ignored", 200

if __name__ == "__main__":
    app.run(port=3000)


