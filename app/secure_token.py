import keyring

SERVICE_NAME = "wb-unit-economics"
USERNAME = "wb-api-token"


def save_token(token: str) -> None:
    keyring.set_password(SERVICE_NAME, USERNAME, token.strip())


def load_token() -> str | None:
    return keyring.get_password(SERVICE_NAME, USERNAME)


def delete_token() -> None:
    try:
        keyring.delete_password(SERVICE_NAME, USERNAME)
    except keyring.errors.PasswordDeleteError:
        pass