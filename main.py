import os
import re
import time

import requests
from dotenv import load_dotenv

from db_manager import db_manager

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("REPO")
WORKFLOW_FILE = os.getenv("WORKFLOW_FILE", "compress-video.yml")
BRANCH = os.getenv("BRANCH", "main")

TG_API = f"https://api.telegram.org/bot{TOKEN}"
GH_API = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"

URL_RE = re.compile(r'https?://\S+')


def send_message(chat_id, text):
    try:
        requests.post(f"{TG_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }, timeout=10)
    except Exception as e:
        print(f"[send_message] {e}")


def trigger_workflow(video_url, chat_id):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "ref": BRANCH,
        "inputs": {
            "video_url": video_url,
            "chat_id": str(chat_id),
        },
    }
    try:
        r = requests.post(GH_API, headers=headers, json=payload, timeout=15)
        if r.status_code == 204:
            return True
        print(f"[workflow] status={r.status_code} body={r.text}")
        return False
    except Exception as e:
        print(f"[workflow] {e}")
        return False


def get_updates(offset=None):
    try:
        r = requests.get(f"{TG_API}/getUpdates", params={
            "timeout": 30,
            "offset": offset,
        }, timeout=40)
        return r.json()
    except Exception as e:
        print(f"[get_updates] {e}")
        return {"result": []}


def handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    if not db_manager.verify_id(chat_id):
        return

    if not text:
        send_message(chat_id, "Mándame un enlace de video para comprimir.")
        return

    if text.startswith("/start"):
        send_message(
            chat_id,
            "👋 Mándame un enlace (YouTube, TikTok, Twitter, o un .mp4 directo) "
            "y te devuelvo el video comprimido a 360p."
        )
        return

    match = URL_RE.search(text)
    if not match:
        send_message(chat_id, "No detecté ningún enlace. Mándame una URL válida.")
        return

    video_url = match.group(0)

    if trigger_workflow(video_url, chat_id):
        send_message(chat_id, "⏳ Procesando tu video, te aviso cuando esté listo.")
    else:
        send_message(chat_id, "❌ No pude iniciar la compresión. Inténtalo más tarde.")


def main():
    print("🤖 Bot iniciado. Esperando mensajes...")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message")
            if msg:
                try:
                    handle_message(msg)
                except Exception as e:
                    print(f"[handle_message] {e}")
        time.sleep(2)


if __name__ == "__main__":
    main()
