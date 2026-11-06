import requests
import json
import os

CONFIG_PATH = os.path.join("data", "telegram_config.json")

def save_telegram_config(token: str, chat_id: str):
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"token": token, "chat_id": chat_id}, f)

def load_telegram_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"token": "", "chat_id": ""}

def send_telegram_message(text: str) -> bool:
    """Отправляет сообщение в Telegram, если настроен токен"""
    config = load_telegram_config()
    token = config.get("token")
    chat_id = config.get("chat_id")
    
    if not token or not chat_id:
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False