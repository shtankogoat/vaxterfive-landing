"""Серверный реестр сессий админки: список активных входов + отзыв.
Правило: сессию можно отозвать только из более старой (раньше созданной) сессии —
новая сессия (например, украденный пароль) не может выкинуть владельца."""
import os, secrets, sqlite3, time
from pathlib import Path

_DB = Path(os.environ.get("ADMIN_DATA", Path(__file__).parent / "data")) / "sessions.sqlite3"
TOUCH_EVERY = 60  # обновляем «последняя активность» не чаще раза в минуту


def _c():
    _DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(_DB, timeout=5)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS sessions(sid TEXT PRIMARY KEY, user TEXT NOT NULL,
                 created REAL NOT NULL, last REAL NOT NULL, ip TEXT, ua TEXT)""")
    return c


def create(user, ip, ua):
    sid = secrets.token_urlsafe(24)
    now = time.time()
    with _c() as c:
        c.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)", (sid, user, now, now, ip, (ua or "")[:200]))
    return sid


def get(sid):
    if not sid:
        return None
    with _c() as c:
        r = c.execute("SELECT * FROM sessions WHERE sid=?", (sid,)).fetchone()
    return dict(r) if r else None


def touch(sid, last_seen):
    now = time.time()
    if now - last_seen >= TOUCH_EVERY:
        with _c() as c:
            c.execute("UPDATE sessions SET last=? WHERE sid=?", (now, sid))


def remove(sid):
    with _c() as c:
        c.execute("DELETE FROM sessions WHERE sid=?", (sid,))


def purge(idle_s, abs_s):
    now = time.time()
    with _c() as c:
        c.execute("DELETE FROM sessions WHERE last<? OR created<?", (now - idle_s, now - abs_s))


def list_for(user):
    with _c() as c:
        return [dict(r) for r in c.execute("SELECT * FROM sessions WHERE user=? ORDER BY created", (user,))]


def revoke(by_sid, target_sid):
    """→ None если отозвано, иначе текст ошибки."""
    me, t = get(by_sid), get(target_sid)
    if not me or not t or t["user"] != me["user"]:
        return "Сессия не найдена."
    if t["sid"] == me["sid"]:
        return "Текущую сессию завершайте кнопкой «Выйти»."
    if t["created"] <= me["created"]:
        return "Более старую сессию нельзя завершить из новой."
    remove(target_sid)
    return None
