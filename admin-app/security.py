"""Доп. слои защиты: TOTP-2FA, уведомления в Telegram."""
import base64, hashlib, hmac, io, logging, os, threading, time
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger("vf_auth")
MSK = timezone(timedelta(hours=3))

# ---------- TOTP ----------
def _fernet():
    k = os.environ.get("TOTP_ENC_KEY") or os.environ["SECRET_KEY"]
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"vf-totp-v1:" + k.encode()).digest()))


def enc(secret):
    return _fernet().encrypt(secret.encode()).decode()


def dec(token):
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def new_secret():
    return pyotp.random_base32()


def verify_code(secret, code, last_step):
    """RFC 6238, шаг 30 с, окно ±1. Возвращает номер шага при успехе (и он должен быть > last_step)."""
    code = "".join(ch for ch in (code or "") if ch.isdigit())
    if len(code) != 6:
        return None
    t = pyotp.TOTP(secret)
    now = int(time.time()) // 30
    for step in (now - 1, now, now + 1):
        if hmac.compare_digest(t.generate_otp(step), code):
            return step if step > (last_step or 0) else None
    return None


def qr_svg_data_uri(secret, login):
    uri = pyotp.TOTP(secret).provisioning_uri(name=login, issuer_name="Vaxter Five admin")
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------- Telegram ----------
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHATS = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()]
TG_PROXY = os.environ.get("TELEGRAM_PROXY", "")


def short_ua(ua):
    ua = ua or ""
    os_ = next((n for k, n in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"), ("Windows", "Windows"),
                               ("Mac OS", "macOS"), ("Linux", "Linux")) if k in ua), "?")
    br = next((n for k, n in (("YaBrowser", "Яндекс"), ("Edg/", "Edge"), ("OPR/", "Opera"), ("Firefox", "Firefox"),
                              ("Chrome", "Chrome"), ("Safari", "Safari")) if k in ua), "?")
    return f"{br}/{os_}"


def _send(text):
    import requests
    proxies = {"http": TG_PROXY, "https": TG_PROXY} if TG_PROXY else None
    for chat in TG_CHATS:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          data={"chat_id": chat, "text": text, "disable_web_page_preview": "true"},
                          proxies=proxies, timeout=8)
        except Exception as e:  # никогда не ломаем вход из-за Telegram
            log.warning("TG_FAIL %s", type(e).__name__)


def alert(event, login, ip, ua):
    try:
        when = datetime.now(MSK).strftime("%d.%m.%Y %H:%M:%S") + " МСК"
        text = f"🔐 Vaxter admin: {event}, логин {login or '-'}, IP {ip}, {short_ua(ua)}, {when}"
        if not (TG_TOKEN and TG_CHATS):
            log.info("TG_SKIP (no token) %s", text)
            return
        threading.Thread(target=_send, args=(text,), daemon=True).start()
    except Exception as e:  # уведомление никогда не должно ломать вход
        log.warning("TG_ERR %s", type(e).__name__)
