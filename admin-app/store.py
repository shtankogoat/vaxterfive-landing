"""Хранилище: пользователи, черновик каталога, бэкапы, публикация, аудит."""
import json, os, re, secrets, subprocess, sys, tempfile, threading
from datetime import datetime
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError

SITE_ROOT = Path(os.environ.get("SITE_ROOT", Path(__file__).resolve().parent.parent)).resolve()
DATA_DIR = Path(os.environ.get("ADMIN_DATA", Path(__file__).resolve().parent / "data")).resolve()
CATALOG = SITE_ROOT / "catalog-src" / "catalog.json"
BUILD = SITE_ROOT / "catalog-src" / "build.py"
IMG_DIR = SITE_ROOT / "img" / "products"
BACKUPS = DATA_DIR / "backups"
DRAFT = DATA_DIR / "draft.json"
USERS = DATA_DIR / "users.json"
AUDIT = DATA_DIR / "audit.log"
KEEP_BACKUPS = 50

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}\.(?:jpg|jpeg|png|webp)$")
USER_RE = re.compile(r"^[a-z0-9_.-]{2,32}$")
BACKUP_RE = re.compile(r"^catalog-\d{8}-\d{6}-\d{6}\.json$")
ITEM_FIELDS = ["short", "fabric", "print", "sizes", "min", "lead"]
DEFAULT_FIELDS = ["fabric", "print", "sizes", "min", "lead"]
FIELD_LABELS = {"name": "Название", "short": "Краткое описание", "fabric": "Материал", "print": "Нанесение",
                "sizes": "Размеры", "min": "Минимальный заказ", "lead": "Сроки", "lead_text": "Описание раздела"}
MAX_LEN = {"name": 120, "short": 400, "fabric": 300, "print": 300, "sizes": 300, "min": 120, "lead": 300,
           "lead_text": 500}

LOCK = threading.RLock()
ph = PasswordHasher()


def ensure_dirs():
    for d in (DATA_DIR, BACKUPS):
        d.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(d, 0o700)
        except OSError:
            pass


def atomic_write(path: Path, data: bytes):
    """Пишем во временный файл в той же папке, fsync, затем os.replace — файл никогда не бывает «наполовину»."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def dump(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


# ---------- аудит ----------
def audit(user, action, detail="", ip=""):
    line = json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "user": user, "ip": ip,
                       "action": action, "detail": detail}, ensure_ascii=False)
    with LOCK, open(AUDIT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_audit(limit=50):
    if not AUDIT.exists():
        return []
    out = []
    for l in reversed(AUDIT.read_text(encoding="utf-8").splitlines()[-limit:]):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


# ---------- пользователи ----------
def load_users():
    if not USERS.exists():
        return {}
    return json.loads(USERS.read_text(encoding="utf-8"))


def save_users(users):
    with LOCK:
        atomic_write(USERS, dump(users))
        try:
            os.chmod(USERS, 0o600)
        except OSError:
            pass


def password_problem(pw):
    if len(pw) < 16:
        return "Пароль должен быть не короче 16 символов."
    if len(pw) > 200:
        return "Слишком длинный пароль."
    if pw.isdigit() or pw.isalpha():
        return "Пароль должен содержать и буквы, и цифры или символы."
    return None


def create_user(username, password, role="manager", display=""):
    username = username.strip().lower()
    if not USER_RE.match(username):
        raise ValueError("Логин: 2–32 символа — латиница a-z, цифры, точка, дефис, подчёркивание.")
    p = password_problem(password)
    if p:
        raise ValueError(p)
    if role not in ("admin", "manager"):
        raise ValueError("Неизвестная роль.")
    with LOCK:
        users = load_users()
        if username in users:
            raise ValueError("Такой пользователь уже есть.")
        users[username] = {"hash": ph.hash(password), "role": role, "display": display.strip()[:60],
                           "created": datetime.now().isoformat(timespec="seconds"), "sv": secrets.token_hex(8)}
        save_users(users)
    return username


def set_password(username, password):
    p = password_problem(password)
    if p:
        raise ValueError(p)
    with LOCK:
        users = load_users()
        users[username]["hash"] = ph.hash(password)
        users[username]["sv"] = secrets.token_hex(8)  # «версия сессии» — инвалидирует все прежние сессии
        save_users(users)
        return users[username]["sv"]


def update_user(username, **fields):
    """Обновить поля пользователя; значение None удаляет поле."""
    with LOCK:
        users = load_users()
        u = users[username]
        for k, v in fields.items():
            if v is None:
                u.pop(k, None)
            else:
                u[k] = v
        save_users(users)


def mark_totp_step(username, step):
    """Атомарно фиксирует использованный шаг TOTP; False — если код уже использован (повтор)."""
    with LOCK:
        users = load_users()
        u = users.get(username)
        if not u or step <= u.get("totp_last", 0):
            return False
        u["totp_last"] = step
        save_users(users)
        return True


def reset_totp(username):
    with LOCK:
        users = load_users()
        u = users[username]
        for k in ("totp_enc", "totp_last", "totp_pending_enc"):
            u.pop(k, None)
        u["sv"] = secrets.token_hex(8)  # выкидываем все сессии
        save_users(users)


_DUMMY = ph.hash("dummy-password-for-constant-timing")


def check_login(username, password):
    username = username.strip().lower()
    users = load_users()
    u = users.get(username)
    try:
        ph.verify(u["hash"] if u else _DUMMY, password)  # всегда считаем хэш — нет утечки по времени
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return None
    if not u:
        return None
    if ph.check_needs_rehash(u["hash"]):
        with LOCK:
            users[username]["hash"] = ph.hash(password)
            save_users(users)
    return u


# ---------- каталог ----------
def read_published():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def load_draft():
    with LOCK:
        if DRAFT.exists():
            return json.loads(DRAFT.read_text(encoding="utf-8"))
        return read_published()


def save_draft(data):
    with LOCK:
        atomic_write(DRAFT, dump(data))


def discard_draft():
    with LOCK:
        DRAFT.unlink(missing_ok=True)


def has_unpublished():
    if not DRAFT.exists():
        return False
    try:
        return json.loads(DRAFT.read_text(encoding="utf-8")) != read_published()
    except (OSError, ValueError):
        return True


def validate(data):
    errs = []
    cats = data.get("categories", [])
    if not cats:
        errs.append("В каталоге нет ни одной категории.")
    seen = set()
    for c in cats:
        cn = c.get("name") or c.get("slug")
        if not SLUG_RE.match(c.get("slug", "")):
            errs.append(f"Категория «{cn}»: некорректный адрес (slug).")
        if c.get("slug") in seen:
            errs.append(f"Адрес категории «{c.get('slug')}» повторяется.")
        seen.add(c.get("slug"))
        if not c.get("name", "").strip():
            errs.append(f"Категория «{c.get('slug')}»: пустое название.")
        if not c.get("items"):
            errs.append(f"Категория «{cn}»: нет товаров — нужен хотя бы один (его фото идёт на обложку).")
        iseen = set()
        for it in c.get("items", []):
            iname = it.get("name") or it.get("slug")
            if not SLUG_RE.match(it.get("slug", "")):
                errs.append(f"Товар «{iname}»: некорректный адрес (slug).")
            if it.get("slug") in iseen:
                errs.append(f"В категории «{cn}» повторяется адрес товара «{it.get('slug')}».")
            iseen.add(it.get("slug"))
            if not it.get("name", "").strip():
                errs.append(f"Товар «{it.get('slug')}» в «{cn}»: пустое название.")
            if not it.get("short", "").strip():
                errs.append(f"Товар «{iname}»: нужно краткое описание.")
            if not it.get("img"):
                errs.append(f"Товар «{iname}»: нет ни одной фотографии.")
            for im in it.get("img", []):
                if not IMG_RE.match(im) or not (IMG_DIR / im).is_file():
                    errs.append(f"Товар «{iname}»: файл фото «{im}» не найден.")
    return errs


def backup_current(reason, user):
    """Байт-в-байт копия текущего catalog.json + ротация до KEEP_BACKUPS последних."""
    ensure_dirs()
    if not CATALOG.exists():
        return None
    name = f"catalog-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
    atomic_write(BACKUPS / name, CATALOG.read_bytes())
    (BACKUPS / (name + ".meta")).write_text(json.dumps({"user": user, "reason": reason}, ensure_ascii=False),
                                            encoding="utf-8")
    for old in sorted(BACKUPS.glob("catalog-*.json"))[:-KEEP_BACKUPS]:
        old.unlink(missing_ok=True)
        Path(str(old) + ".meta").unlink(missing_ok=True)
    return name


def list_backups():
    out = []
    for f in sorted(BACKUPS.glob("catalog-*.json"), reverse=True):
        if not BACKUP_RE.match(f.name):
            continue
        meta = {}
        m = Path(str(f) + ".meta")
        if m.exists():
            try:
                meta = json.loads(m.read_text(encoding="utf-8"))
            except ValueError:
                pass
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            cats, items = len(d["categories"]), sum(len(c["items"]) for c in d["categories"])
        except Exception:
            cats = items = "?"
        ts = datetime.strptime(f.name[8:23], "%Y%m%d-%H%M%S")
        out.append({"name": f.name, "ts": ts, "cats": cats, "items": items, **meta})
    return out


def run_build():
    r = subprocess.run([sys.executable, str(BUILD)], cwd=str(SITE_ROOT), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=120,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode == 0, (r.stdout + r.stderr).strip()[-3000:]


def publish_bytes(raw: bytes, user, reason):
    """Бэкап → атомарная запись catalog.json → сборка. Если сборка упала — откат к прежнему файлу."""
    with LOCK:
        prev = CATALOG.read_bytes() if CATALOG.exists() else None
        backup_current(reason, user)
        atomic_write(CATALOG, raw)
        ok, log = run_build()
        if not ok and prev is not None:
            atomic_write(CATALOG, prev)
            run_build()
        return ok, log


def publish_draft(user):
    with LOCK:
        data = load_draft()
        errs = validate(data)
        if errs:
            return False, errs, ""
        ok, log = publish_bytes(dump(data), user, "Публикация")
        if ok:
            discard_draft()
        return ok, ([] if ok else ["Сборка завершилась с ошибкой, изменения откатены."]), log


def restore_backup(name, user):
    if not BACKUP_RE.match(name):
        raise ValueError("bad name")
    raw = (BACKUPS / name).read_bytes()
    errs = validate(json.loads(raw.decode("utf-8")))
    if errs:
        return False, errs, ""
    with LOCK:
        ok, log = publish_bytes(raw, user, f"Восстановление {name}")
        if ok:
            discard_draft()
    return ok, ([] if ok else ["Сборка завершилась с ошибкой."]), log

