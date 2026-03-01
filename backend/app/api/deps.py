import hashlib
import hmac
import json
from typing import Optional
from urllib.parse import parse_qsl, unquote
from fastapi import HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.session import get_db
from app.db.models import User


def validate_init_data(init_data: str) -> dict:
    """Validate Telegram WebApp initData HMAC-SHA256."""
    parsed = dict(parse_qsl(unquote(init_data), keep_blank_values=True))
    hash_value = parsed.pop("hash", "")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    secret_key = hmac.new(
        b"WebAppData",
        settings.BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()

    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, hash_value):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    return parsed


async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None),
    x_web_password: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Web browser password auth
    if x_web_password is not None:
        if not settings.WEB_PASSWORD or x_web_password != settings.WEB_PASSWORD:
            raise HTTPException(status_code=401, detail="Invalid password")
        q = await db.execute(select(User).where(User.is_admin == True).limit(1))
        admin = q.scalar_one_or_none()
        if not admin:
            raise HTTPException(status_code=401, detail="No admin user configured")
        return admin

    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        parsed = validate_init_data(x_telegram_init_data)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid initData")

    user_data = json.loads(parsed.get("user", "{}"))
    user_id = user_data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="No user in initData")

    q = await db.execute(select(User).where(User.id == user_id))
    user = q.scalar_one_or_none()

    if not user:
        user = User(
            id=user_id,
            username=user_data.get("username"),
            full_name=f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
            is_admin=user_id in settings.ADMIN_IDS,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if user_id in settings.ADMIN_IDS and not user.is_admin:
            user.is_admin = True
            await db.commit()

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")

    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user
