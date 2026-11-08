"""Заявки с сайта: проверка, надёжное сохранение (SQLite + leads.jsonl), отправка в AmoCRM в фоне."""
import json, logging, os, re, sqlite3, threading, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("vf_leads")
MSK = timezone(timedelta(hours=3))

MAX_FILE = 10 * 1024 * 1024
EXTS = {"jpg", "jpeg", "png", "webp", "pdf", "ai", "cdr", "psd", "zip"}
DESIGN = {"Да", "Нет", "Есть пример"}
MAT = {"Знаю", "Помощь"}
VIA = {"Звонок", "MAX", "Telegram", "ВКонтакте"}
PHONE_RE = re.compile(r"^\+?[\d\s()\-]{10,20}$")
TG_RE = re.compile(r"^@[A-Za-z0-9_]{4,32}$")
KIT_RE = re.compile(r"^https://vaxterfive\.ru/#k=[A-Za-z0-9_\-.~%=&+]{1,4000}$")
RATE = ((10 * 60, 5), (24 * 3600, 30))  # окно, максимум заявок с одного IP

_DB = _DIR = _JSONL = None
_local = threading.local()
_lock = threading.Lock()


def init(data_dir: Path):
    global _DB, _DIR, _JSONL
    _DIR = Path(data_dir) / "lead-files"
    _DIR.mkdir(parents=True, exist_ok=True)
    _JSONL = Path(data_dir) / "leads.jsonl"
    _DB = str(Path(data_dir) / "leads.sqlite3")
    c = _conn()
    c.execute("""CREATE TABLE IF NOT EXISTS leads (id TEXT PRIMARY KEY, ts REAL, ip TEXT, data TEXT,
                 file TEXT, file_name TEXT, status TEXT, amo_id INTEGER, error TEXT, sent_ts REAL)""")
    c.execute("CREATE TABLE IF NOT EXISTS lead_hits (ip TEXT, ts REAL)")
    c.execute("CREATE INDEX IF NOT EXISTS lead_hits_i ON lead_hits(ip, ts)")
    for p in (_DB, _DIR):
        try:
            os.chmod(p, 0o700 if p == _DIR else 0o600)
        except OSError:
            pass


def _conn():
    c = getattr(_local, "c", None)
    if c is None:
        c = sqlite3.connect(_DB, timeout=10, isolation_level=None)
        c.execute("PRAGMA journal_mode=WAL")
        c.row_factory = sqlite3.Row
        _local.c = c
    return c


# ---------- лимит по IP ----------
def rate_limited(ip):
    now = time.time()
    c = _conn()
    c.execute("DELETE FROM lead_hits WHERE ts < ?", (now - 86400,))
    for window, lim in RATE:
        if c.execute("SELECT count(*) FROM lead_hits WHERE ip=? AND ts>=?", (ip, now - window)).fetchone()[0] >= lim:
            return True
    return False


def hit(ip):
    _conn().execute("INSERT INTO lead_hits VALUES (?,?)", (ip, time.time()))


# ---------- проверка ----------
def _sniff(head, ext):
    if ext in ("jpg", "jpeg"):
        return head[:3] == b"\xff\xd8\xff"
    if ext == "png":
        return head[:8] == b"\x89PNG\r\n\x1a\n"
    if ext == "webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if ext == "pdf":
        return head[:5] == b"%PDF-"
    if ext == "ai":
        return head[:5] == b"%PDF-" or head[:4] == b"%!PS"
    if ext == "psd":
        return head[:4] == b"8BPS"
    if ext == "zip":
        return head[:4] in (b"PK\x03\x04", b"PK\x05\x06")
    if ext == "cdr":
        return (head[:4] == b"RIFF" and head[8:11] == b"CDR") or head[:4] == b"PK\x03\x04"
    return False


def validate(form, files):
    """→ (data, file_bytes, ext, orig_name) или raise ValueError(сообщение по-русски)."""
    g = lambda k: " ".join((form.get(k) or "").split()) if k != "what" else (form.get(k) or "").strip()
    what, name, contact = g("what"), g("name"), g("contact")
    if not what:
        raise ValueError("Опишите, что нужно сшить.")
    if len(what) > 2000:
        raise ValueError("Описание слишком длинное (до 2000 символов).")
    if not name or len(name) > 100:
        raise ValueError("Укажите имя (до 100 символов).")
    if not contact or len(contact) > 100:
        raise ValueError("Укажите телефон или @telegram.")
    if not (PHONE_RE.match(contact) and 10 <= len(re.sub(r"\D", "", contact)) <= 15) and not TG_RE.match(contact):
        raise ValueError("Контакт: телефон (например +7 900 123-45-67) или ник Telegram (@username).")
    if form.get("consent") != "Да":
        raise ValueError("Нужно согласие на обработку персональных данных.")
    qty = None
    if form.get("qty"):
        try:
            qty = int(form.get("qty"))
            assert 1 <= qty <= 1_000_000
        except (ValueError, AssertionError):
            raise ValueError("Количество — целое число от 1 до 1 000 000.")
    date = g("date") or None
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Дата в формате ГГГГ-ММ-ДД.")
    design, mat = g("design") or None, g("mat") or None
    if design and design not in DESIGN:
        raise ValueError("Некорректное значение поля «Дизайн».")
    if mat and mat not in MAT:
        raise ValueError("Некорректное значение поля «Материал».")
    via = g("via") or None
    if via and via not in VIA:
        raise ValueError("Некорректный способ связи.")
    page = g("page")[:500] or None
    if page and not page.startswith(("https://vaxterfive.ru", "http://127.0.0.1", "http://localhost")):
        page = None
    kit = g("kit") or None
    if kit and not KIT_RE.match(kit):
        raise ValueError("Некорректная ссылка на конструктор.")
    blob = ext = orig = None
    f = files.get("attachment")
    if f and f.filename:
        orig = re.sub(r"[^\w.\- ()]", "_", Path(f.filename).name)[:120]
        ext = orig.rsplit(".", 1)[-1].lower() if "." in orig else ""
        if ext not in EXTS:
            raise ValueError("Файл: допустимы JPG, PNG, WEBP, PDF, AI, CDR, PSD, ZIP.")
        blob = f.stream.read(MAX_FILE + 1)
        if len(blob) > MAX_FILE:
            raise ValueError("Файл больше 10 МБ.")
        if not blob or not _sniff(blob[:16], ext):
            raise ValueError("Файл повреждён или не соответствует расширению.")
        ext = "jpg" if ext == "jpeg" else ext
    data = {"what": what, "qty": qty, "date": date, "design": design, "mat": mat, "via": via, "name": name,
            "contact": contact, "consent": "Да", "page": page, "kit": kit}
    return data, blob, ext, orig


# ---------- хранение ----------
def save(data, blob, ext, orig, ip, ua):
    lid = uuid.uuid4().hex
    fname = None
    if blob:
        fname = f"{uuid.uuid4().hex}.{ext}"
        (_DIR / fname).write_bytes(blob)
    rec = {"id": lid, "ts": time.time(), "ip": ip, "ua": ua[:200], **data, "file": fname, "file_name": orig}
    with _lock, open(_JSONL, "a", encoding="utf-8") as fh:  # «сырой» журнал — заявка не потеряется даже при сбое БД
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    _conn().execute("INSERT INTO leads VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (lid, rec["ts"], ip, json.dumps({**data, "ua": ua[:200]}, ensure_ascii=False), fname, orig,
                     "pending" if amo_configured() else "not_configured", None, None, None))
    return lid


def get(lid):
    r = _conn().execute("SELECT * FROM leads WHERE id=?", (lid,)).fetchone()
    return _row(r) if r else None


def _row(r):
    d = dict(r)
    d["data"] = json.loads(d["data"])
    d["when"] = datetime.fromtimestamp(d["ts"], MSK).strftime("%d.%m.%Y %H:%M")
    return d


KEEP = 50  # в админке храним 50 последних заявок; остальное — в AmoCRM


def list_all(limit=KEEP):
    return [_row(r) for r in _conn().execute(
        "SELECT * FROM leads ORDER BY ts DESC LIMIT ?", (limit,))]


def file_path(lead):
    if not lead or not lead["file"] or not re.fullmatch(r"[0-9a-f]{32}\.[a-z]{2,4}", lead["file"]):
        return None
    p = (_DIR / lead["file"]).resolve()
    return p if p.parent == _DIR.resolve() and p.is_file() else None


def _set(lid, **kw):
    cols = ", ".join(f"{k}=?" for k in kw)
    _conn().execute(f"UPDATE leads SET {cols} WHERE id=?", (*kw.values(), lid))


# ---------- AmoCRM ----------
def amo_configured():
    return bool(os.environ.get("AMO_SUBDOMAIN") and os.environ.get("AMO_TOKEN"))


def _amo_base():
    return os.environ.get("AMO_BASE_URL") or f"https://{os.environ['AMO_SUBDOMAIN']}.amocrm.ru"


def _is_phone(s):
    return bool(PHONE_RE.match(s)) and 10 <= len(re.sub(r"\D", "", s)) <= 15


def _tg_link(s):
    return f"https://t.me/{s[1:]}" if s and TG_RE.match(s) else None


def note_text(lead, file_url):
    d = lead["data"]
    rows = [("Что сшить", d.get("what")), ("Количество", d.get("qty")), ("Срок", d.get("date")),
            ("Дизайн", d.get("design")), ("Материал", d.get("mat")), ("Имя", d.get("name")),
            ("Контакт", d.get("contact")), ("Telegram", _tg_link(d.get("contact"))),
            ("Как связаться", d.get("via")), ("Конструктор", d.get("kit")),
            ("Файл", f"{lead['file_name']} — {file_url} (нужен вход в админку)" if lead.get("file") else None),
            ("Страница", d.get("page")), ("IP", lead.get("ip")), ("Время", lead.get("when") + " МСК")]
    return "Заявка с сайта vaxterfive.ru\n\n" + "\n".join(f"{k}: {v}" for k, v in rows if v not in (None, ""))


def send_to_amo(lid, file_url):
    import requests
    lead = get(lid)
    if not lead:
        return
    if not amo_configured():
        _set(lid, status="not_configured")
        return
    d = lead["data"]
    proxy = os.environ.get("AMO_PROXY")
    kw = dict(headers={"Authorization": f"Bearer {os.environ['AMO_TOKEN']}"}, timeout=8,
              proxies={"http": proxy, "https": proxy} if proxy else None)
    contact = {"first_name": d["name"]}
    if _is_phone(d["contact"]):
        contact["custom_fields_values"] = [{"field_code": "PHONE",
                                            "values": [{"value": d["contact"], "enum_code": "WORK"}]}]
    elif _tg_link(d["contact"]):
        contact["custom_fields_values"] = [{"field_code": "IM",
                                            "values": [{"value": _tg_link(d["contact"]), "enum_code": "OTHER"}]}]
    if d.get("via"):
        contact["first_name"] = f'{d["name"]} ({d["via"]})'
    body = {"name": "Заявка с сайта: " + d["what"][:60],
            "custom_fields_values": [{"field_id": 776497, "values": [{"value": "сайт"}]}],
            "_embedded": {"tags": [{"name": "Сайт"}], "contacts": [contact]}}
    if d.get("qty"):
        body["custom_fields_values"].append({"field_id": 808751, "values": [{"value": int(d["qty"])}]})  # Изделий в заказе
    if d.get("date"):
        ts = int(datetime.strptime(d["date"], "%Y-%m-%d").replace(hour=12).timestamp())
        body["custom_fields_values"].append({"field_id": 808187, "values": [{"value": ts}]})  # DeadLine
    for env, key in (("AMO_PIPELINE_ID", "pipeline_id"), ("AMO_STATUS_ID", "status_id"),
                     ("AMO_RESPONSIBLE_USER_ID", "responsible_user_id")):
        if os.environ.get(env, "").isdigit():
            body[key] = int(os.environ[env])
    try:
        r = requests.post(_amo_base() + "/api/v4/leads/complex", json=[body], **kw)
        if r.status_code == 400 and contact.get("custom_fields_values", [{}])[0].get("field_code") == "IM":
            contact.pop("custom_fields_values")  # нет поля IM в аккаунте — ссылка всё равно в примечании
            r = requests.post(_amo_base() + "/api/v4/leads/complex", json=[body], **kw)
        r.raise_for_status()
        amo_id = int(r.json()[0]["id"])
        r2 = requests.post(f"{_amo_base()}/api/v4/leads/{amo_id}/notes",
                           json=[{"note_type": "common", "params": {"text": note_text(lead, file_url)}}], **kw)
        r2.raise_for_status()
        _set(lid, status="sent", amo_id=amo_id, error=None, sent_ts=time.time())
        log.info("LEAD_AMO_OK id=%s amo=%s", lid, amo_id)
    except Exception as e:
        msg = f"{type(e).__name__}: {getattr(getattr(e, 'response', None), 'status_code', '')} {str(e)[:200]}"
        _set(lid, status="error", error=msg)
        log.warning("LEAD_AMO_FAIL id=%s %s", lid, msg)


def send_async(lid, file_url):
    threading.Thread(target=send_to_amo, args=(lid, file_url), daemon=True).start()


def delete(lid):
    """Удаляет заявку из админки: строка в БД, приложенный файл и запись в «сыром» журнале. AmoCRM не трогаем."""
    lead = get(lid)
    if not lead:
        return False
    _conn().execute("DELETE FROM leads WHERE id=?", (lid,))
    if lead.get("file"):
        try:
            (_DIR / lead["file"]).unlink()
        except FileNotFoundError:
            pass
    with _lock:
        if _JSONL.exists():
            keep = [l for l in _JSONL.read_text(encoding="utf-8").splitlines()
                    if l.strip() and json.loads(l).get("id") != lid]
            tmp = _JSONL.with_suffix(".tmp")
            tmp.write_text("".join(k + "\n" for k in keep), encoding="utf-8")
            os.replace(tmp, _JSONL)
    return True


def prune(keep=KEEP):
    """Строго 50 последних заявок: пришла новая — самая старая удаляется (вся история — в AmoCRM)."""
    old = [r[0] for r in _conn().execute(
        "SELECT id FROM leads WHERE id NOT IN (SELECT id FROM leads ORDER BY ts DESC LIMIT ?)", (keep,))]
    for lid in old:
        delete(lid)
    return len(old)
