import bcrypt
from database import get_session
from models import User


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_user(username: str, password: str, display_name: str = ""):
    session = get_session()
    try:
        if session.query(User).filter_by(username=username).first():
            raise ValueError(f"帳號 {username} 已存在")
        user = User(
            username=username,
            password_hash=_hash_password(password),
            display_name=display_name or username,
        )
        session.add(user)
        session.commit()
        return user.id
    finally:
        session.close()


def verify_login(username: str, password: str) -> bool:
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username, is_active=True).first()
        if not user:
            return False
        return _verify_password(password, user.password_hash)
    finally:
        session.close()
