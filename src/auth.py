
import json
import hashlib
import hmac
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
AUTH_FILE = BASE_DIR / "data" / "users.json"


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_users():
    if not AUTH_FILE.exists():
        return []

    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as file:
            users = json.load(file)

        return users if isinstance(users, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_users(users):
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(AUTH_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, indent=4)


def create_admin(company_name, name, email, password):
    users = load_users()

    if any(user.get("role") == "Admin" for user in users):
        return False, "Admin account pehle se bana hua hai."

    if any(user.get("email", "").lower() == email.strip().lower() for user in users):
        return False, "Ye email pehle se registered hai."

    users.append({
        "id": 1,
        "company": company_name.strip(),
        "name": name.strip(),
        "email": email.strip().lower(),
        "password_hash": hash_password(password),
        "role": "Admin"
    })

    save_users(users)
    return True, "Admin account successfully create ho gaya!"


def authenticate(email, password):
    users = load_users()
    entered_hash = hash_password(password)

    for user in users:
        saved_email = user.get("email", "")
        saved_hash = user.get("password_hash", "")
        if (
            isinstance(saved_email, str)
            and isinstance(saved_hash, str)
            and saved_email.lower() == email.strip().lower()
            and hmac.compare_digest(saved_hash, entered_hash)
        ):
            return user

    return None
