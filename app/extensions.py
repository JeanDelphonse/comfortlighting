from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _user_key():
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return f"user:{current_user.id}"
    except Exception:
        pass
    return get_remote_address()


limiter = Limiter(key_func=_user_key, storage_uri="memory://", default_limits=[])
