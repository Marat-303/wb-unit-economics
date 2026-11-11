import keyring
import os

SERVICE_NAME = "wb-unit-economics"
USERNAME = "wb-api-token"
TOKEN_FILE = os.path.join("data", "token.txt")

def save_token(token: str) -> None:
    token = token.strip()
    os.makedirs("data", exist_ok=True)
    # Сохраняем в файл (для Linux)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token)
    # Пытаемся сохранить в Keyring (для Windows)
    try:
        keyring.set_password(SERVICE_NAME, USERNAME, token)
    except Exception:
        pass

def load_token() -> str | None:
    # Сначала проверяем файл (для сервера)
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                token = f.read().strip()
                if token:
                    return token
        except Exception:
            pass
            
    # Если файла нет, пробуем Keyring (для Windows)
    try:
        return keyring.get_password(SERVICE_NAME, USERNAME)
    except Exception:
        return None

def delete_token() -> None:
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
        except Exception:
            pass
            
    try:
        keyring.delete_password(SERVICE_NAME, USERNAME)
    except Exception:
        pass