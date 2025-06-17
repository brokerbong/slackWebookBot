from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from slack_sdk import WebClient
import os
import requests
import fitz  # PyMuPDF
from io import BytesIO
import uvicorn
from typing import Optional, Dict, Any, List

from datetime import datetime, timedelta
import httpx
import asyncio
import asyncpg
import json


app = FastAPI()

NXOPEN_API_KEY = os.getenv("NEXON_API_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# FastAPI 시작/종료 시점에 DB 연결 풀 생성/닫기
@app.on_event("startup")
async def on_startup():
    app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

@app.on_event("shutdown")
async def on_shutdown():
    await app.state.db_pool.close()


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


@app.get("/heroes/{ocid}/mondays")
async def fetch_hero_mondays(
    ocid: str,
    start_date: str = "2023-12-25",
    end_date:   str = "2025-06-16",):
    # 날짜 파싱 및 유효성 검사
    try:
        s = datetime.strptime(start_date, "%Y-%m-%d")
        e = datetime.strptime(end_date,   "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식은 YYYY-MM-DD 여야 합니다.")
    if s > e:
        raise HTTPException(status_code=400, detail="start_date가 end_date보다 이후일 수 없습니다.")

    # 첫 월요일 계산 (0=월요일 … 6=일요일)
    days_until_monday = (0 - s.weekday() + 7) % 7
    current = s + timedelta(days=days_until_monday)

    url_tpl = "https://open.api.nexon.com/maplestory/v1/character/stat?ocid={ocid}&date={date}"
    headers = {"x-nxopen-api-key": NXOPEN_API_KEY}
    pool = app.state.db_pool

    inserted = 0
    async with httpx.AsyncClient(timeout=20.0) as client:
        while current <= e:
            ds = current.strftime("%Y%m%d")
            url = url_tpl.format(ocid=ocid, date=ds)

            resp = await client.get(url, headers=headers)
            print(f"[{ds}] status={resp.status_code}  body={resp.text[:200]}")
            entry = {
                "ocid": ocid,
                "date": current.date(),  # DATE 타입으로
                "data": resp.json()
            }
            # DB에 INSERT
            await pool.execute(
                """
                INSERT INTO character_original_data (ocid, date, data)
                VALUES ($1, $2, $3::jsonb)
                """,
                entry["ocid"],
                entry["date"],
                json.dumps(entry["data"])
            )
            inserted += 1

            # 초당 5회 제한 준수
            await asyncio.sleep(0.3)
            current += timedelta(days=7)

    return JSONResponse({
        "ocid":     ocid,
        "from":     start_date,
        "to":       end_date,
        "mondays":  inserted,
        "status":   "inserted into hero_history"
    })



@app.post("/")
async def index():
    
    return PlainTextResponse("")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=3000, reload=True)
