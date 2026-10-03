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

ESCALAS = ["1080", "720", "480", "360", "240", "144"]

pendientes = {}  # {chat_id: {"video_url": str, "message_id": int}}


def send_message(chat_id, text):
    try:
        requests.post(f"{TG_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }, timeout=10)
    except Exception as e:
        print(f"[send_message] {e}")


def send_message_with_keyboard(chat_id, text, keyboard):
    try:
        r = requests.post(f"{TG_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": keyboard,
        }, timeout=10)
        return r.json().get("result", {}).get("message_id")
    except Exception as e:
        print(f"[send_message_with_keyboard] {e}")
        return None


def edit_message(chat_id, message_id, text):
    try:
        requests.post(f"{TG_API}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }, timeout=10)
    except Exception as e:
        print(f"[edit_message] {e}")


def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    try:
        requests.post(f"{TG_API}/answerCallbackQuery", json=payload, timeout=10)
    except Exception as e:
        print(f"[answer_callback] {e}")


def teclado_escalas():
    filas = []
    for i in range(0, len(ESCALAS), 3):
        fila = [
            {"text": f"🎬 {e}p", "callback_data": f"scale:{e}"}
            for e in ESCALAS[i:i + 3]
        ]
        filas.append(fila)
    return {"inline_keyboard": filas}


def trigger_workflow(video_url, chat_id, scale):
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
            "scale": scale,
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
            "👋 Bienvenido a Video Compress\n\n 🔗 Envíame un enlace directo de un video o de alguna red social, me encargo de descargarlo y comprimirlo.\n\n📲 Múltiples plataformas soportadas, ejemplo:\n -YouTube\n -TikTok\n -Instragram\n -Muchos más\n\n💛 Que disfrutes"
        )
        return

    match = URL_RE.search(text)
    if not match:
        send_message(chat_id, "❓ No detecté ningún enlace. Mándame una URL válida.")
        return

    video_url = match.group(0)

    message_id = send_message_with_keyboard(
        chat_id,
        "🎚️ Selecciona la escala de salida:",
        teclado_escalas()
    )

    if message_id:
        pendientes[chat_id] = {
            "video_url": video_url,
            "message_id": message_id,
        }
    else:
        send_message(chat_id, "❌ No pude mostrar las opciones. Inténtalo de nuevo.")


def handle_callback(cq):
    chat_id = cq["message"]["chat"]["id"]
    message_id = cq["message"]["message_id"]
    data = cq.get("data", "")

    answer_callback(cq["id"])

    if not data.startswith("scale:"):
        return

    escala = data.split(":", 1)[1]

    if escala not in ESCALAS:
        edit_message(chat_id, message_id, "❌ Escala no válida.")
        return

    info = pendientes.pop(chat_id, None)
    if not info:
        edit_message(chat_id, message_id, "⚠️ Sesión expirada. Manda el enlace otra vez.")
        return

    edit_message(chat_id, message_id, f"⏳ Procesando en {escala}p...")

    if trigger_workflow(info["video_url"], chat_id, escala):
        edit_message(chat_id, message_id, f"⏳ Procesando en {escala}p. Te aviso cuando esté listo.")
    else:
        edit_message(chat_id, message_id, "❌ No pude iniciar la compresión. Inténtalo más tarde.")


def main():
    print("🤖 Bot iniciado. Esperando mensajes...")
    offset = None
    try:
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
                    continue

                cq = update.get("callback_query")
                if cq:
                    try:
                        handle_callback(cq)
                    except Exception as e:
                        print(f"[handle_callback] {e}")
            time.sleep(2)
    finally:
        db_manager.close()


if __name__ == "__main__":
    main()
