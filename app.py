from flask import Flask, request, jsonify
from slack_sdk import WebClient
import os

app = Flask(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

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
            channel = event.get("channel")
            user = event.get("user")
            text = event.get("text")

            slack_client.chat_postMessage(channel=channel, text=text)
        
        return "", 200

    return "Ignored", 200

if __name__ == "__main__":
    app.run(port=3000)
