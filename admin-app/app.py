"""Админка каталога Vaxter Five (Flask). Отдаётся по секретному префиксу ADMIN_PREFIX через nginx → 127.0.0.1:5600."""
import io, logging, os, re, secrets, sys, time
from collections import defaultdict, deque
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import (Flask, Response, abort, flash, g, redirect, render_template, request, send_from_directory,
                   session, url_for)
from werkzeug.exceptions import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

APP_DIR = Path(__file__).resolve().parent


def _load_env_file():
    """Локально читаем admin-app/.env (на сервере переменные даёт systemd EnvironmentFile)."""
    f = Path(os.environ.get("ADMIN_ENV_FILE", APP_DIR / ".env"))
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env_file()
import store as S  # noqa: E402  (после чтения .env — store берёт SITE_ROOT/ADMIN_DATA из окружения)
import security as SEC  # noqa: E402
import sessions as SS  # noqa: E402

SECRET = os.environ.get("SECRET_KEY", "")
if len(SECRET) < 32:
    sys.exit("SECRET_KEY не задан или короче 32 символов (см. README: python manage.py gen-secret).")

DEV = os.environ.get("ADMIN_DEV") == "1"
IDLE_MIN = int(os.environ.get("SESSION_IDLE_MINUTES", "30"))
ABS_HOURS = int(os.environ.get("SESSION_MAX_HOURS", "8"))
MAX_FILE = 15 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 60_000_000  # защита от «декомпрессионных бомб»

PREFIX_RAW = os.environ.get("ADMIN_PREFIX", "").strip()
if not re.fullmatch(r"/[A-Za-z0-9_-]{1,80}/?", PREFIX_RAW):
    sys.exit("ADMIN_PREFIX: ожидается вида /vf-случайная-строка/")
P = "/" + PREFIX_RAW.strip("/")  # без завершающего слэша

app = Flask(__name__, static_url_path=P + "/static", static_folder="static")
app.config.update(
    SECRET_KEY=SECRET,
    SESSION_COOKIE_NAME="vf_admin",
    SESSION_COOKIE_PATH=P,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") != "0",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=ABS_HOURS),
    MAX_CONTENT_LENGTH=10 * MAX_FILE,  # до 10 файлов за раз; каждый ещё проверяется отдельно
    TEMPLATES_AUTO_RELOAD=DEV,
)
if os.environ.get("BEHIND_PROXY") == "1":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

S.ensure_dirs()
auth_log = logging.getLogger("vf_auth")
auth_log.setLevel(logging.INFO)
_h = logging.FileHandler(S.DATA_DIR / "auth.log", encoding="utf-8")
_h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
auth_log.addHandler(_h)

# ---------- ограничение попыток входа ----------
import throttle as TH  # noqa: E402
TH.init(S.DATA_DIR)  # счётчики неудачных входов — в SQLite, общие для воркеров и переживают рестарт
import leads as LD  # noqa: E402
LD.init(S.DATA_DIR)
SITE_URL = os.environ.get("SITE_URL", "https://vaxterfive.ru").rstrip("/")
LEAD_ORIGINS = {"https://vaxterfive.ru", "https://www.vaxterfive.ru"}


def login_blocked(ip, user):
    return TH.retry_after(ip, user) > 0


def ip():
    return request.remote_addr or "-"


# ---------- безопасность запросов ----------
CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; script-src 'self'; form-action 'self'; frame-ancestors 'none'; "
       "base-uri 'none'; object-src 'none'")


@app.after_request
def headers(resp):
    resp.headers["Content-Security-Policy"] = CSP
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.path.startswith(P) and not request.path.startswith(P + "/static"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token
app.jinja_env.globals["site_url"] = os.environ.get("SITE_URL", "https://vaxterfive.ru/")
app.jinja_env.globals["LABELS"] = S.FIELD_LABELS


PUBLIC_ENDPOINTS = ("login", "totp", "totp_setup", "static")
# ТЕСТ: TOTP_DISABLED=1 в env — вход только по логину/паролю (2FA-код остаётся в коде, включается удалением флага)
TOTP_DISABLED = os.environ.get("TOTP_DISABLED") == "1"
PENDING_TTL = 5 * 60


def ua():
    return request.headers.get("User-Agent", "")[:300]


def event(action, login, detail="", alert_text=None):
    """Аудит + (при необходимости) уведомление в Telegram."""
    S.audit(login or "-", action, detail, ip())
    if alert_text:
        SEC.alert(alert_text, login, ip(), ua())


def plain_404():
    """Вне секретного префикса — ровно та же 404, что у публичного сайта (админка ничем себя не выдаёт)."""
    try:
        body = (S.SITE_ROOT / "errors" / "404.html").read_bytes()
    except OSError:
        body = b"<!doctype html><meta charset=utf-8><title>404</title><h1>404</h1>"
    return Response(body, 404, mimetype="text/html")


def dev_site_path(path):
    return DEV and re.match(r"^/(img|css|js|catalog|articles)(/|$)", path)


@app.before_request
def guard():
    if request.path == "/api/lead":  # единственный публичный маршрут — своя защита внутри
        return None
    # 0) всё вне секретного префикса — просто 404 без подсказок
    if not (request.path == P or request.path.startswith(P + "/")) and not dev_site_path(request.path):
        return plain_404()
    if request.method == "POST":
        tok = request.form.get("csrf", "")
        if not tok or not secrets.compare_digest(tok, session.get("csrf", "")):
            abort(400, "CSRF")
    g.user = None
    uname = session.get("user")
    if uname:
        u = S.load_users().get(uname)
        now = time.time()
        rec = SS.get(session.get("sid"))
        if (not u or not rec or rec["user"] != uname or session.get("sv") != u.get("sv")
                or (not TOTP_DISABLED and not u.get("totp_enc"))
                or now - session.get("last", 0) > IDLE_MIN * 60 or now - session.get("t0", 0) > ABS_HOURS * 3600):
            if rec:
                SS.remove(rec["sid"])
            session.clear()
            if request.endpoint not in PUBLIC_ENDPOINTS:
                flash("Сессия завершена — войдите снова.", "info")
                return redirect(url_for("login"))
        else:
            SS.touch(rec["sid"], rec["last"])
            session["last"] = now
            g.sid = rec["sid"]
            g.user = {"name": uname, **u}


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not g.user:
            return redirect(url_for("login"))
        return f(*a, **k)
    return w


def admin_required(f):
    @wraps(f)
    @login_required
    def w(*a, **k):
        if g.user["role"] != "admin":
            abort(403)
        return f(*a, **k)
    return w


def log(action, detail=""):
    S.audit(g.user["name"] if g.user else "-", action, detail, ip())


@app.context_processor
def ctx():
    return {"me": g.get("user"), "unpublished": g.get("user") and S.has_unpublished()}


# ---------- помощники каталога ----------
def clean(v, key):
    return " ".join((v or "").split())  # схлопываем пробелы/переводы строк; длину проверяет text_error


def get_cat(data, slug):
    for c in data["categories"]:
        if c["slug"] == slug:
            return c
    abort(404)


def get_item(cat, slug):
    for it in cat["items"]:
        if it["slug"] == slug:
            return it
    abort(404)


def move(lst, idx, d):
    j = idx + d
    if 0 <= idx < len(lst) and 0 <= j < len(lst):
        lst[idx], lst[j] = lst[j], lst[idx]


def slug_error(slug, existing):
    if not S.SLUG_RE.match(slug) or len(slug) > 60:
        return "Адрес (slug): только латиница a-z, цифры и дефис, например «winter-jacket»."
    if slug in existing:
        return "Такой адрес уже занят."
    if slug == "page":
        return "Адрес «page» зарезервирован для страниц каталога — выберите другой."
    return None


def text_error(fields):
    for k, v in fields.items():
        if len(v) > S.MAX_LEN.get(k, 300):
            return f"Поле «{S.FIELD_LABELS.get(k, k)}» слишком длинное (максимум {S.MAX_LEN.get(k, 300)})."
        if any(ord(ch) < 32 and ch not in "\n\t" for ch in v):
            return f"Поле «{S.FIELD_LABELS.get(k, k)}» содержит недопустимые символы."
    return None


# ---------- вход: пароль → (обязательная настройка) 2FA ----------
def pending_user():
    """Пользователь, прошедший пароль, но ещё не 2FA (живёт 5 минут)."""
    name, t = session.get("pending"), session.get("pending_t", 0)
    if not name or time.time() - t > PENDING_TTL:
        return None, None
    u = S.load_users().get(name)
    if not u or u.get("sv") != session.get("pending_sv"):
        return None, None
    return name, u


def fail(kind, user):
    TH.record(ip(), user)
    auth_log.warning("%s ip=%s user=%s", kind, ip(), user)
    label = {"LOGIN_FAIL": "неверный пароль", "TOTP_FAIL": "неверный код 2FA"}[kind]
    event("Неудачный вход: " + label, user, "", label)
    if login_blocked(ip(), user):
        auth_log.warning("LOGIN_BLOCKED ip=%s user=%s", ip(), user)
        event("Блокировка входа на 15 мин", user, "", "блокировка после неудачных попыток")
    time.sleep(TH.penalty_delay(user))  # растущая задержка против перебора


def blocked_response(tpl, user, **kw):
    auth_log.warning("LOGIN_BLOCKED ip=%s user=%s", ip(), user)
    return render_error(429, retry=max(60, TH.retry_after(ip(), user)))


def finish_login(name, u):
    session.clear()  # защита от фиксации сессии
    session.permanent = True
    SS.purge(IDLE_MIN * 60, ABS_HOURS * 3600)
    sid = SS.create(name, ip(), ua())
    session.update(user=name, sid=sid, sv=u["sv"], t0=time.time(), last=time.time(), csrf=secrets.token_urlsafe(32))
    TH.clear_user(name)
    auth_log.info("LOGIN_OK ip=%s user=%s", ip(), name)
    event("Вход", name, SEC.short_ua(ua()), "успешный вход")
    return redirect(url_for("home"))


@app.route(P + "/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("home"))
    if request.method == "POST":
        user = request.form.get("username", "").strip().lower()[:64]
        pw = request.form.get("password", "")[:200]
        if login_blocked(ip(), user):
            return blocked_response("login.html", user)
        u = S.check_login(user, pw)
        if not u:
            fail("LOGIN_FAIL", user)
            flash("Неверный логин или пароль.", "error")
            return render_template("login.html"), 401
        session.clear()
        session.update(pending=user, pending_sv=u["sv"], pending_t=time.time(), csrf=secrets.token_urlsafe(32))
        auth_log.info("PASSWORD_OK ip=%s user=%s", ip(), user)
        S.audit(user, "Пароль верный, ожидается код 2FA", "", ip())
        if TOTP_DISABLED:
            return finish_login(user, u)
        return redirect(url_for("totp" if u.get("totp_enc") else "totp_setup"))
    return render_template("login.html")


@app.route(P + "/2fa", methods=["GET", "POST"])
def totp():
    name, u = pending_user()
    if not name:
        session.clear()
        return redirect(url_for("login"))
    if not u.get("totp_enc"):
        return redirect(url_for("totp_setup"))
    if request.method == "POST":
        if login_blocked(ip(), name):
            return blocked_response("totp.html", name)
        secret = SEC.dec(u["totp_enc"])
        step = SEC.verify_code(secret, request.form.get("code"), u.get("totp_last", 0)) if secret else None
        if step is None or not S.mark_totp_step(name, step):
            fail("TOTP_FAIL", name)
            flash("Неверный или уже использованный код. Дождитесь нового кода в приложении.", "error")
            return render_template("totp.html"), 401
        return finish_login(name, S.load_users()[name])
    return render_template("totp.html")


@app.route(P + "/2fa/setup", methods=["GET", "POST"])
def totp_setup():
    name, u = pending_user()
    if not name:
        session.clear()
        return redirect(url_for("login"))
    if u.get("totp_enc"):
        return redirect(url_for("totp"))
    secret = SEC.dec(u["totp_pending_enc"]) if u.get("totp_pending_enc") else None
    if not secret:
        secret = SEC.new_secret()
        S.update_user(name, totp_pending_enc=SEC.enc(secret))
    kw = dict(qr=SEC.qr_svg_data_uri(secret, name), secret=secret)
    if request.method == "POST":
        if login_blocked(ip(), name):
            return blocked_response("totp_setup.html", name, **kw)
        step = SEC.verify_code(secret, request.form.get("code"), 0)
        if step is None:
            fail("TOTP_FAIL", name)
            flash("Код не подошёл. Проверьте, что время на телефоне точное, и введите свежий код.", "error")
            return render_template("totp_setup.html", **kw), 401
        S.update_user(name, totp_enc=SEC.enc(secret), totp_last=step, totp_pending_enc=None)
        event("2FA подключена", name, "", "подключена двухфакторная защита")
        return finish_login(name, S.load_users()[name])
    return render_template("totp_setup.html", **kw)


@app.post(P + "/logout")
def logout():
    if g.user:
        log("Выход")
        SS.remove(session.get("sid"))
    session.clear()
    return redirect(url_for("login"))


# ---------- категории ----------
@app.get(P + "/")
@login_required
def home():
    return render_template("home.html", data=S.load_draft())


@app.post(P + "/cat/new")
@login_required
def cat_new():
    data = S.load_draft()
    name, slug = clean(request.form.get("name"), "name"), request.form.get("slug", "").strip().lower()
    lead = clean(request.form.get("lead_text"), "lead_text")
    err = (None if name else "Укажите название.") or slug_error(slug, {c["slug"] for c in data["categories"]}) \
        or text_error({"name": name, "lead_text": lead})
    if err:
        flash(err, "error")
        return redirect(url_for("home"))
    data["categories"].append({"slug": slug, "name": name, "lead_text": lead, "items": []})
    save_and_publish(data)
    log("Создана категория", f"{slug} «{name}»")
    flash(f"Категория «{name}» создана. Добавьте в неё товары.", "ok")
    return redirect(url_for("cat", slug=slug))


@app.route(P + "/cat/<slug>", methods=["GET", "POST"])
@login_required
def cat(slug):
    data = S.load_draft()
    c = get_cat(data, slug)
    if request.method == "POST":
        name, new = clean(request.form.get("name"), "name"), request.form.get("slug", "").strip().lower()
        lead = clean(request.form.get("lead_text"), "lead_text")
        others = {x["slug"] for x in data["categories"] if x is not c}
        err = (None if name else "Укажите название.") or slug_error(new, others) \
            or text_error({"name": name, "lead_text": lead})
        if err:
            flash(err, "error")
        else:
            c.update(name=name, slug=new, lead_text=lead)
            pub = save_and_publish(data)
            log("Изменена категория", f"{slug} → {new} «{name}»")
            if pub:
                flash("Сохранено и опубликовано на сайте.", "ok")
            return redirect(url_for("cat", slug=new))
    return render_template("cat.html", c=c, data=data)


@app.post(P + "/cat/<slug>/move")
@login_required
def cat_move(slug):
    data = S.load_draft()
    c = get_cat(data, slug)
    move(data["categories"], data["categories"].index(c), -1 if request.form.get("dir") == "up" else 1)
    save_and_publish(data)
    log("Порядок категорий", slug)
    return redirect(url_for("home"))


@app.post(P + "/cat/<slug>/delete")
@login_required
def cat_delete(slug):
    data = S.load_draft()
    c = get_cat(data, slug)
    data["categories"].remove(c)
    save_and_publish(data)
    log("Удалена категория", f"{slug} «{c['name']}» ({len(c['items'])} тов.)")
    flash(f"Категория «{c['name']}» удалена с сайта.", "ok")
    return redirect(url_for("home"))


# ---------- товары ----------
def item_from_form(data, cat, item=None):
    f = request.form
    vals = {"name": clean(f.get("name"), "name")}
    for k in S.ITEM_FIELDS:
        vals[k] = clean(f.get(k), k)
    slug = f.get("slug", "").strip().lower()
    target = get_cat(data, f.get("category", cat["slug"]))
    existing = {x["slug"] for x in target["items"] if x is not item}
    err = (None if vals["name"] else "Укажите название.") or slug_error(slug, existing) or text_error(vals) \
        or (None if vals["short"] else "Нужно краткое описание.")
    return err, slug, vals, target


def apply_item(it, slug, vals):
    new = {"slug": slug, "name": vals["name"], "img": it.get("img", []), "short": vals["short"]}
    for k in ("fabric", "print", "sizes", "min", "lead"):
        if vals[k]:  # пустое поле = берётся значение «по умолчанию»
            new[k] = vals[k]
    for k, v in it.items():  # сохраняем неизвестные ключи, если кто-то добавил их вручную
        if k not in new and k not in S.ITEM_FIELDS and k not in ("slug", "name", "img"):
            new[k] = v
    it.clear()
    it.update(new)


@app.route(P + "/cat/<slug>/new", methods=["GET", "POST"])
@login_required
def item_new(slug):
    data = S.load_draft()
    c = get_cat(data, slug)
    if request.method == "POST":
        err, islug, vals, target = item_from_form(data, c)
        if err:
            flash(err, "error")
            return render_template("item.html", c=c, it=None, form=request.form, data=data)
        it = {}
        apply_item(it, islug, vals)
        target["items"].append(it)
        save_and_publish(data)
        log("Создан товар", f"{target['slug']}/{islug} «{vals['name']}»")
        flash("Товар создан. Теперь загрузите фотографии.", "ok")
        return redirect(url_for("item", slug=target["slug"], islug=islug) + "#photos")
    return render_template("item.html", c=c, it=None, form={}, data=data)


@app.route(P + "/cat/<slug>/<islug>", methods=["GET", "POST"])
@login_required
def item(slug, islug):
    data = S.load_draft()
    c = get_cat(data, slug)
    it = get_item(c, islug)
    if request.method == "POST":
        err, new, vals, target = item_from_form(data, c, it)
        if err:
            flash(err, "error")
            return render_template("item.html", c=c, it=it, form=request.form, data=data)
        apply_item(it, new, vals)
        if target is not c:
            c["items"].remove(it)
            target["items"].append(it)
        pub = save_and_publish(data)
        log("Изменён товар", f"{slug}/{islug} → {target['slug']}/{new}")
        if pub:
            flash("Сохранено и опубликовано на сайте.", "ok")
        return redirect(url_for("item", slug=target["slug"], islug=new))
    published = (S.SITE_ROOT / "catalog" / slug / islug / "index.html").is_file()
    return render_template("item.html", c=c, it=it, form=it, data=data, published=published)


@app.post(P + "/cat/<slug>/<islug>/move")
@login_required
def item_move(slug, islug):
    data = S.load_draft()
    c = get_cat(data, slug)
    it = get_item(c, islug)
    move(c["items"], c["items"].index(it), -1 if request.form.get("dir") == "up" else 1)
    save_and_publish(data)
    log("Порядок товаров", f"{slug}/{islug}")
    return redirect(url_for("cat", slug=slug) + "#items")


@app.post(P + "/cat/<slug>/<islug>/delete")
@login_required
def item_delete(slug, islug):
    data = S.load_draft()
    c = get_cat(data, slug)
    it = get_item(c, islug)
    c["items"].remove(it)
    save_and_publish(data)
    log("Удалён товар", f"{slug}/{islug} «{it['name']}»")
    flash(f"Товар «{it['name']}» удалён с сайта.", "ok")
    return redirect(url_for("cat", slug=slug) + "#items")


# ---------- фото ----------
def process_image(fs):
    """Проверка и пере-кодирование: имени и метаданным пользователя не доверяем."""
    ext = Path(fs.filename or "").suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise ValueError(f"«{fs.filename}»: допустимы только JPG, PNG, WEBP.")
    raw = fs.stream.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise ValueError(f"«{fs.filename}»: файл больше 15 МБ.")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format
            probe.verify()
        if fmt not in ("JPEG", "PNG", "WEBP"):
            raise ValueError
        im = Image.open(io.BytesIO(raw))
        im.load()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError, SyntaxError):
        raise ValueError(f"«{fs.filename}»: это не изображение или файл повреждён.")
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((2000, 2000), Image.LANCZOS)
    name = f"u-{secrets.token_hex(8)}.jpg"
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85, optimize=True, progressive=True)  # без EXIF/GPS
    dest = (S.IMG_DIR / name).resolve()
    if dest.parent != S.IMG_DIR.resolve():
        raise ValueError("path")
    S.atomic_write(dest, out.getvalue())
    return name


MAX_PHOTOS = 9
app.jinja_env.globals["MAX_PHOTOS"] = MAX_PHOTOS


@app.post(P + "/cat/<slug>/<islug>/photos")
@login_required
def photo_upload(slug, islug):
    files = [f for f in request.files.getlist("photos") if f and f.filename]
    if not files:
        flash("Выберите файлы.", "error")
        return redirect(url_for("item", slug=slug, islug=islug) + "#photos")
    have = len(get_item(get_cat(S.load_draft(), slug), islug).get("img", []))
    room = MAX_PHOTOS - have
    if room <= 0:
        flash(f"У товара уже {MAX_PHOTOS} фото — это максимум. Удалите лишнее, чтобы загрузить новое.", "error")
        return redirect(url_for("item", slug=slug, islug=islug) + "#photos")
    if len(files) > room:
        flash(f"Максимум {MAX_PHOTOS} фото на товар: сейчас {have}, можно добавить ещё {room}.", "error")
        return redirect(url_for("item", slug=slug, islug=islug) + "#photos")
    added = []
    for f in files:
        try:
            added.append(process_image(f))
        except ValueError as e:
            flash(str(e), "error")
    if added:
        with S.LOCK:
            data = S.load_draft()
            it = get_item(get_cat(data, slug), islug)
            imgs = it.setdefault("img", [])
            imgs.extend(added[:max(0, MAX_PHOTOS - len(imgs))])
            save_and_publish(data)
        log("Загружены фото", f"{slug}/{islug}: {', '.join(added)}")
        flash(f"Загружено фото: {len(added)}.", "ok")
    return redirect(url_for("item", slug=slug, islug=islug) + "#photos")


@app.post(P + "/cat/<slug>/<islug>/photo")
@login_required
def photo_action(slug, islug):
    data = S.load_draft()
    it = get_item(get_cat(data, slug), islug)
    imgs = it.get("img", [])
    try:
        i = int(request.form.get("i", ""))
        assert 0 <= i < len(imgs)
    except (ValueError, AssertionError):
        abort(400)
    act, name = request.form.get("act"), imgs[i]
    if act == "up":
        move(imgs, i, -1)
    elif act == "down":
        move(imgs, i, 1)
    elif act == "cover":
        imgs.insert(0, imgs.pop(i))
    elif act == "delete":
        imgs.pop(i)  # файл не удаляем: он может понадобиться при восстановлении старой версии
    else:
        abort(400)
    save_and_publish(data)
    log({"up": "Фото выше", "down": "Фото ниже", "cover": "Обложка", "delete": "Удалено фото"}[act],
        f"{slug}/{islug}: {name}")
    return redirect(url_for("item", slug=slug, islug=islug) + "#photos")


# ---------- значения по умолчанию ----------
@app.route(P + "/defaults", methods=["GET", "POST"])
@login_required
def defaults():
    data = S.load_draft()
    if request.method == "POST":
        vals = {k: clean(request.form.get(k), k) for k in S.DEFAULT_FIELDS}
        err = text_error(vals)
        if err:
            flash(err, "error")
        else:
            d = data.setdefault("defaults", {})
            for k, v in vals.items():
                if v:
                    d[k] = v
                else:
                    d.pop(k, None)
            pub = save_and_publish(data)
            log("Изменены значения по умолчанию")
            if pub:
                flash("Сохранено и опубликовано на сайте.", "ok")
            return redirect(url_for("defaults"))
    return render_template("defaults.html", d=data.get("defaults", {}))


# ---------- публикация и версии ----------
def save_and_publish(data):
    """Каждое сохранение сразу публикуется на сайт (черновик + сборка каталога)."""
    S.save_draft(data)
    ok, errs, out = S.publish_draft(g.user["name"])
    log("Публикация" if ok else "Публикация не удалась", "; ".join(errs)[:500] or out[-200:])
    if not ok:
        for e in errs:
            flash("Сохранено, но не опубликовано: " + e, "error")
    return ok


@app.post(P + "/publish")
@login_required
def publish():
    ok, errs, out = S.publish_draft(g.user["name"])
    log("Публикация" if ok else "Публикация не удалась", "; ".join(errs)[:500] or out[-200:])
    if ok:
        flash("Опубликовано! Страницы каталога пересобраны. " + out, "ok")
    else:
        for e in errs:
            flash(e, "error")
        if out:
            flash(out[-600:], "error")
    return redirect(request.form.get("back") if (request.form.get("back") or "").startswith(P + "/") and "//" not in request.form.get("back")
                    else url_for("home"))


@app.post(P + "/discard")
@login_required
def discard():
    S.discard_draft()
    log("Черновик сброшен")
    flash("Неопубликованные изменения отменены.", "ok")
    return redirect(url_for("home"))


@app.get(P + "/versions")
@login_required
def versions():
    return render_template("versions.html", backups=S.list_backups())


@app.post(P + "/versions/restore")
@login_required
def version_restore():
    name = request.form.get("name", "")
    try:
        ok, errs, out = S.restore_backup(name, g.user["name"])
    except (ValueError, FileNotFoundError):
        abort(400)
    log("Восстановлена версия" if ok else "Восстановление не удалось", name)
    flash(f"Версия {name} восстановлена и опубликована." if ok else "; ".join(errs), "ok" if ok else "error")
    return redirect(url_for("versions"))


# ---------- пользователи ----------
@app.get(P + "/users")
@admin_required
def users():
    return render_template("users.html", users=S.load_users())


@app.post(P + "/users/new")
@admin_required
def user_new():
    try:
        u = S.create_user(request.form.get("username", ""), request.form.get("password", ""),
                          request.form.get("role", "manager"), request.form.get("display", ""))
        log("Добавлен пользователь", f"{u} ({request.form.get('role')})")
        SEC.alert(f"создан пользователь {u} (админ {g.user['name']})", g.user["name"], ip(), ua())
        flash(f"Пользователь {u} добавлен. Передайте ему пароль лично.", "ok")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("users"))


@app.post(P + "/users/delete")
@admin_required
def user_delete():
    name = request.form.get("username", "")
    with S.LOCK:
        us = S.load_users()
        if name == g.user["name"]:
            flash("Нельзя удалить самого себя.", "error")
        elif name in us:
            if us[name]["role"] == "admin" and sum(1 for x in us.values() if x["role"] == "admin") <= 1:
                flash("Нельзя удалить последнего администратора.", "error")
            else:
                us.pop(name)
                S.save_users(us)
                log("Удалён пользователь", name)
                SEC.alert(f"удалён пользователь {name} (админ {g.user['name']})", g.user["name"], ip(), ua())
                flash(f"Пользователь {name} удалён.", "ok")
    return redirect(url_for("users"))


@app.post(P + "/users/reset-2fa")
@admin_required
def user_reset_2fa():
    name = request.form.get("username", "")
    if name == g.user["name"]:
        flash("Свою 2FA сбросить нельзя — попросите другого администратора или используйте manage.py reset-2fa.", "error")
    elif name in S.load_users():
        S.reset_totp(name)
        log("Сброшена 2FA", name)
        SEC.alert(f"сброшена 2FA пользователя {name} (админ {g.user['name']})", g.user["name"], ip(), ua())
        flash(f"2FA пользователя {name} сброшена: при следующем входе он настроит её заново.", "ok")
    return redirect(url_for("users"))


@app.route(P + "/password", methods=["GET", "POST"])
@login_required
def password():
    if request.method == "POST":
        if not S.check_login(g.user["name"], request.form.get("old", "")):
            flash("Текущий пароль неверен.", "error")
        elif request.form.get("new") != request.form.get("new2"):
            flash("Новые пароли не совпадают.", "error")
        else:
            try:
                session["sv"] = S.set_password(g.user["name"], request.form.get("new", ""))
                log("Сменён пароль")
                flash("Пароль изменён. Остальные сессии завершены.", "ok")
                return redirect(url_for("home"))
            except ValueError as e:
                flash(str(e), "error")
    return render_template("password.html")


@app.get(P + "/sessions")
@login_required
def sessions_page():
    SS.purge(IDLE_MIN * 60, ABS_HOURS * 3600)
    rows = SS.list_for(g.user["name"])
    me = next((r for r in rows if r["sid"] == g.sid), None)
    for r in rows:
        r["ua_short"] = SEC.short_ua(r["ua"])
        r["created_s"] = time.strftime("%d.%m.%Y %H:%M", time.localtime(r["created"]))
        r["last_s"] = time.strftime("%d.%m.%Y %H:%M", time.localtime(r["last"]))
        r["me"] = r["sid"] == g.sid
        r["can"] = bool(me) and r["created"] > me["created"]
    return render_template("sessions.html", rows=rows)


@app.post(P + "/sessions/revoke")
@login_required
def sessions_revoke():
    target = request.form.get("sid", "")
    if target == "newer":
        me = SS.get(g.sid)
        n = 0
        for r in SS.list_for(g.user["name"]):
            if me and r["created"] > me["created"]:
                SS.remove(r["sid"]); n += 1
        log("Завершены сессии", f"новее текущей: {n}")
        flash(f"Завершено сессий: {n}." if n else "Более новых сессий нет.", "info")
    else:
        err = SS.revoke(g.sid, target)
        if err:
            flash(err, "error")
        else:
            log("Сессия завершена", "")
            flash("Сессия завершена.", "info")
    return redirect(url_for("sessions_page"))


@app.get(P + "/audit")
@admin_required
def audit_page():
    return render_template("audit.html", rows=S.read_audit())


# ---------- публичный приём заявок с лендинга ----------
def _origin_ok():
    src = request.headers.get("Origin") or ""
    if not src:
        ref = request.headers.get("Referer") or ""
        m = re.match(r"^(https?://[^/]+)", ref)
        src = m.group(1) if m else ""
    if src in LEAD_ORIGINS:
        return True
    return DEV and bool(re.match(r"^http://(127\.0\.0\.1|localhost)(:\d+)?$", src))


def lead_file_url(lid):
    return f"{SITE_URL}{P}/leads/{lid}/file"


@app.post("/api/lead")
def api_lead():
    if not _origin_ok():
        auth_log.warning("LEAD_BAD_ORIGIN ip=%s origin=%s", ip(), request.headers.get("Origin", "-")[:100])
        return {"ok": False, "error": "Запрос отклонён."}, 403
    if LD.rate_limited(ip()):
        auth_log.warning("LEAD_RATE ip=%s", ip())
        return {"ok": False, "error": "Слишком много заявок с вашего адреса. Попробуйте позже или позвоните нам."}, 429
    LD.hit(ip())
    if (request.form.get("website") or "").strip():  # ловушка для ботов — делаем вид, что всё хорошо
        auth_log.warning("LEAD_HONEYPOT ip=%s", ip())
        return {"ok": True}
    try:
        data, blob, ext, orig = LD.validate(request.form, request.files)
    except ValueError as e:
        return {"ok": False, "error": str(e)}, 400
    lid = LD.save(data, blob, ext, orig, ip(), ua())
    try:
        LD.prune()  # строго 50 последних: новая пришла — самая старая удаляется
    except Exception:
        app.logger.exception("leads prune failed")
    S.audit("сайт", "Новая заявка", f"{lid[:8]} {data['name']} / {data['contact']}", ip())
    if LD.amo_configured():
        LD.send_async(lid, lead_file_url(lid))
    return {"ok": True, "code": lid[:8]}


@app.get(P + "/leads")
@login_required
def leads_page():
    return render_template("leads.html", leads=LD.list_all(), amo=LD.amo_configured())


@app.get(P + "/leads/<lid>/file")
@login_required
def lead_file(lid):
    if not re.fullmatch(r"[0-9a-f]{32}", lid):
        abort(404)
    lead = LD.get(lid)
    fp = LD.file_path(lead)
    if not fp:
        abort(404)
    log("Скачан файл заявки", lid[:8])
    return send_from_directory(fp.parent, fp.name, as_attachment=True,
                               download_name=lead["file_name"] or fp.name, max_age=0)


@app.post(P + "/leads/<lid>/resend")
@login_required
def lead_resend(lid):
    if not re.fullmatch(r"[0-9a-f]{32}", lid) or not LD.get(lid):
        abort(404)
    if not LD.amo_configured():
        flash("AmoCRM не настроен — укажите AMO_SUBDOMAIN и AMO_TOKEN в env.", "error")
    else:
        LD.send_to_amo(lid, lead_file_url(lid))  # синхронно, чтобы сразу показать результат
        st = LD.get(lid)
        flash("Заявка отправлена в AmoCRM." if st["status"] == "sent" else f"Ошибка AmoCRM: {st['error']}",
              "ok" if st["status"] == "sent" else "error")
    log("Повторная отправка заявки в AMO", lid[:8])
    return redirect(url_for("leads_page"))


@app.post(P + "/leads/<lid>/delete")
@login_required
def lead_delete(lid):
    if not re.fullmatch(r"[0-9a-f]{32}", lid) or not LD.delete(lid):
        abort(404)
    log("Удалена заявка", lid[:8])
    flash("Заявка удалена из админки (в AmoCRM она осталась).", "ok")
    return redirect(url_for("leads_page"))


# ---------- статьи (блог) — отдельный модуль ----------
import articles_routes  # noqa: E402
articles_routes.register(app, {"P": P, "login_required": login_required, "save_and_publish": save_and_publish, "log": log})


ERRORS = {
    400: ("Запрос не принят", "Скорее всего, страница была открыта слишком долго и форма устарела. Обновите страницу и повторите действие."),
    403: ("Нет доступа", "Этот раздел доступен только администратору."),
    404: ("Страница не найдена", "Такой страницы в панели нет — возможно, товар или категорию уже переименовали или удалили."),
    405: ("Так нельзя", "Это действие выполняется только кнопкой в интерфейсе панели."),
    413: ("Слишком большой файл", "Фото должно быть не больше 15 МБ, за раз — до 10 файлов."),
    429: ("Слишком много попыток", "Вход временно заблокирован для защиты от подбора пароля."),
    500: ("Что-то пошло не так", "Ошибка на сервере. Изменения в черновике сохранены — попробуйте ещё раз через минуту."),
}


def render_error(code, retry=None):
    if not (request.path == P or request.path.startswith(P + "/")):
        return plain_404()
    title, msg = ERRORS.get(code, ("Ошибка", ""))
    resp = app.make_response((render_template("error.html", code=code, title=title, msg=msg, retry=retry), code))
    if retry:
        resp.headers["Retry-After"] = str(retry)
    return resp


@app.errorhandler(HTTPException)
def http_err(e):
    if request.path == "/api/lead":
        msg = "Файл слишком большой (до 10 МБ)." if e.code == 413 else "Запрос не принят."
        return {"ok": False, "error": msg}, (e.code if e.code in (405, 413) else 400)
    return render_error(e.code if e.code in ERRORS else 500)


@app.errorhandler(Exception)
def server_err(e):
    app.logger.exception("Unhandled error")
    return render_error(500)


# ---------- только для локальной разработки: раздаём сайт, чтобы работали превью ----------
if DEV:
    @app.get("/img/<path:p>")
    def dev_img(p):
        return send_from_directory(S.SITE_ROOT / "img", p)

    @app.get("/<any(css,js):d>/<path:p>")
    def dev_assets(d, p):
        return send_from_directory(S.SITE_ROOT / d, p)

    @app.get("/catalog/")
    @app.get("/catalog/<path:p>")
    def dev_catalog(p=""):
        return send_from_directory(S.SITE_ROOT / "catalog", (p.rstrip("/") + "/index.html").lstrip("/"))

    @app.get("/articles/")
    @app.get("/articles/<path:p>")
    def dev_articles(p=""):
        return send_from_directory(S.SITE_ROOT / "articles", (p.rstrip("/") + "/index.html").lstrip("/"))


@app.get(P)
def no_slash():
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5600")), debug=False)
