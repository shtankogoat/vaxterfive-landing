"""Счётчики неудачных входов в SQLite (WAL): переживают рестарт, общие для всех воркеров/потоков.

Политика:
  * по IP — жёстко: 5 неудач (пароль или код 2FA) за 15 мин → блок IP на 15 мин (+ fail2ban на уровне фаервола);
  * по логину — мягко: 20 неудач за 15 мин → блок логина, плюс растущая задержка ответа после каждой неудачи.
    Так злоумышленник, знающий логин, не может одной-двумя попытками «запереть» настоящего админа,
    а перебор с многих IP всё равно упирается в лимит логина.
"""
import os, sqlite3, threading, time
from pathlib import Path

WINDOW = 15 * 60
IP_LIMIT = 5
USER_LIMIT = 20
_local = threading.local()
_DB = None


def init(data_dir: Path):
    global _DB
    _DB = str(Path(data_dir) / "throttle.sqlite3")
    c = _conn()
    c.execute("CREATE TABLE IF NOT EXISTS fails (kind TEXT NOT NULL, key TEXT NOT NULL, ts REAL NOT NULL)")
    c.execute("CREATE INDEX IF NOT EXISTS fails_k ON fails(kind, key, ts)")
    c.commit()
    try:
        os.chmod(_DB, 0o600)
    except OSError:
        pass


def _conn():
    c = getattr(_local, "c", None)
    if c is None or getattr(_local, "db", None) != _DB:
        c = sqlite3.connect(_DB, timeout=10, isolation_level=None)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        _local.c, _local.db = c, _DB
    return c


def record(ip, user):
    now = time.time()
    c = _conn()
    c.execute("BEGIN IMMEDIATE")
    c.execute("DELETE FROM fails WHERE ts < ?", (now - WINDOW,))
    c.executemany("INSERT INTO fails VALUES (?,?,?)", [("ip", ip, now), ("user", user, now)])
    c.execute("COMMIT")


def _times(kind, key):
    rows = _conn().execute("SELECT ts FROM fails WHERE kind=? AND key=? AND ts>=? ORDER BY ts",
                           (kind, key, time.time() - WINDOW)).fetchall()
    return [r[0] for r in rows]


def retry_after(ip, user):
    """0 — можно; иначе секунды до разблокировки."""
    now, waits = time.time(), []
    for kind, key, lim in (("ip", ip, IP_LIMIT), ("user", user, USER_LIMIT)):
        t = _times(kind, key)
        if len(t) >= lim:
            waits.append(t[len(t) - lim] + WINDOW - now)
    return int(max(waits)) + 1 if waits else 0


def user_fail_count(user):
    return len(_times("user", user))


def penalty_delay(user):
    """Небольшая растущая задержка после неудачи: 0.5, 1, 2, 4 с (максимум)."""
    n = user_fail_count(user)
    return min(4.0, 0.25 * (2 ** min(n, 5))) if n else 0.0


def clear_user(user):
    _conn().execute("DELETE FROM fails WHERE kind='user' AND key=?", (user,))
