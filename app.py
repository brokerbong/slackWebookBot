from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()

    # Slack URL 인증용 응답
    if data.get("type") == "url_verification":
        return data.get("challenge"), 200, {"Content-Type": "text/plain"}

    # 일반 이벤트 처리
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        print("Received event:", event)
        # 여기에 이벤트에 따라 로직 추가 가능
        return "", 200

    return "Ignored", 200

if __name__ == "__main__":
    app.run(port=3000)
