"""Статьи (блог): санитайзер HTML, транслитерация slug, обработка картинок для /img/articles/.
Статьи хранятся в том же catalog.json (ключ "articles") — значит, у них те же черновик, версии,
бэкапы и автопубликация, что и у каталога."""
import io, re, secrets
from datetime import date
from html import escape
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

import store as S

ART_IMG_DIR = S.SITE_ROOT / "img" / "articles"
ART_IMG_RE = re.compile(r"^/img/articles/a-[0-9a-f]{16}\.webp$")
MAX_IMG = 15 * 1024 * 1024
MAX_BODY = 200_000
MAX_LEN = {"title": 160, "excerpt": 300, "slug": 80}
RESERVED = {"page"}

# ---------- slug ----------
_TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
               ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t",
                "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))


def translit(s):
    t = "".join(_TR.get(ch, ch) for ch in (s or "").lower())
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:MAX_LEN["slug"]].strip("-")


def slug_problem(slug, taken):
    if not S.SLUG_RE.match(slug or "") or len(slug) > MAX_LEN["slug"]:
        return "Адрес (slug): только латиница a-z, цифры и дефис, например «kak-vybrat-formu»."
    if slug in RESERVED:
        return "Адрес «page» зарезервирован для страниц списка — выберите другой."
    if slug in taken:
        return "Статья с таким адресом уже есть."
    return None


# ---------- магические байты (как в leads.py) ----------
def sniff(head):
    if head[:3] == b"\xff\xd8\xff":
        return "JPEG"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "WEBP"
    return None


def process_image(fs, max_side=1600):
    """Проверка по магическим байтам → Pillow → webp (без EXIF) в /img/articles/. → (url, w, h)."""
    raw = fs.stream.read(MAX_IMG + 1)
    if len(raw) > MAX_IMG:
        raise ValueError("Файл больше 15 МБ.")
    kind = sniff(raw[:16])
    if not kind:
        raise ValueError("Допустимы только JPG, PNG или WEBP.")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format
            probe.verify()
        if fmt != kind:
            raise ValueError
        im = Image.open(io.BytesIO(raw))
        im.load()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError, SyntaxError):
        raise ValueError("Это не изображение или файл повреждён.")
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((max_side, max_side), Image.LANCZOS)
    name = f"a-{secrets.token_hex(8)}"
    ART_IMG_DIR.mkdir(parents=True, exist_ok=True)
    out = io.BytesIO()
    im.save(out, "WEBP", quality=82, method=6)
    dest = (ART_IMG_DIR / f"{name}.webp").resolve()
    if dest.parent != ART_IMG_DIR.resolve():
        raise ValueError("path")
    S.atomic_write(dest, out.getvalue())
    if im.width > 800:  # уменьшенная копия для карточек и мобильных
        sm = im.resize((800, round(im.height * 800 / im.width)), Image.LANCZOS)
        o2 = io.BytesIO()
        sm.save(o2, "WEBP", quality=82, method=6)
        S.atomic_write(ART_IMG_DIR / f"{name}-800.webp", o2.getvalue())
    return f"/img/articles/{name}.webp", im.width, im.height


# ---------- санитайзер ----------
ALLOWED = {"p", "h2", "h3", "strong", "em", "ul", "ol", "li", "a", "blockquote", "figure", "img", "figcaption", "br"}
RENAME = {"b": "strong", "i": "em", "div": "p", "h1": "h2", "h4": "h3", "h5": "h3", "h6": "h3"}
DROP_CONTENT = {"script", "style", "iframe", "object", "embed", "template", "noscript", "svg", "math", "head", "title",
                "textarea", "select", "button"}
VOID = {"img", "br"}
BLOCK = {"p", "h2", "h3", "ul", "ol", "blockquote", "figure"}
HREF_RE = re.compile(r"^(https?://[^\s\"'<>]+|mailto:[^\s\"'<>]+|tel:\+?[0-9()\- ]+|/[^\s\"'<>]*|#[\w-]*)$", re.I)


class _San(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.stack, self.skip = [], [], 0
        self.fig = None  # {"img": ..., "cap": [...]} — фигуру собираем целиком

    def _open(self, tag):
        return tag in self.stack

    def handle_starttag(self, tag, attrs):
        tag = RENAME.get(tag, tag)
        if self.skip or tag in DROP_CONTENT:
            if tag not in VOID:
                self.skip += 1
            return
        if tag not in ALLOWED:
            return
        a = dict(attrs)
        if tag == "img":
            src = (a.get("src") or "").strip()
            if not ART_IMG_RE.match(src):
                return
            if self.fig is not None:
                self.fig["img"] = src
            else:  # одиночная картинка → своя фигура без подписи
                self._close_inline_blocks()
                self.out.append(f'<figure><img src="{src}" alt=""></figure>')
            return
        if tag == "figure":
            self._close_inline_blocks()
            self.fig = {"img": None, "cap": []}
            self.stack.append("figure")
            return
        if tag == "figcaption":
            if self.fig is not None:
                self.stack.append("figcaption")
            return
        if self._open("figure"):  # внутри фигуры — только текст подписи
            return
        if tag == "br":
            self.out.append("<br>")
            return
        if tag in BLOCK and tag not in ("ul", "ol") and any(t in ("p", "h2", "h3") for t in self.stack):
            self._close_inline_blocks()  # блок внутри абзаца — закрываем абзац
        if tag == "li" and not any(t in ("ul", "ol") for t in self.stack):
            tag = "p"
        if tag == "a":
            href = (a.get("href") or "").strip()
            if not HREF_RE.match(href) or self._open("a"):
                return
            ext = href.lower().startswith(("http://", "https://")) and "vaxterfive.ru" not in href.lower().split("/")[2]
            self.out.append(f'<a href="{escape(href)}"' + (' target="_blank" rel="noopener nofollow"' if ext else "") + ">")
            self.stack.append("a")
            return
        self.out.append(f"<{tag}>")
        self.stack.append(tag)

    def _close_inline_blocks(self):
        while self.stack and self.stack[-1] in ("p", "h2", "h3", "strong", "em", "a"):
            self.out.append(f"</{self.stack.pop()}>")

    def handle_endtag(self, tag):
        tag = RENAME.get(tag, tag)
        if tag in DROP_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag not in self.stack:
            return
        if tag == "figure":
            while self.stack and self.stack[-1] != "figure":
                self.stack.pop()
            self.stack.pop()
            f, self.fig = self.fig, None
            if f and f["img"]:
                cap = " ".join("".join(f["cap"]).split())[:300]
                self.out.append(f'<figure><img src="{f["img"]}" alt="{escape(cap)}">'
                                + (f"<figcaption>{escape(cap)}</figcaption>" if cap else "") + "</figure>")
            return
        if tag == "figcaption":
            if self.stack[-1] == "figcaption":
                self.stack.pop()
            return
        while self.stack:
            t = self.stack.pop()
            self.out.append(f"</{t}>")
            if t == tag:
                break

    def handle_data(self, data):
        if self.skip:
            return
        if self.fig is not None:
            if self._open("figcaption"):
                self.fig["cap"].append(data)
            return
        if not self.stack and data.strip():  # голый текст → абзац
            self.out.append("<p>")
            self.stack.append("p")
        if self.stack and self.stack[-1] in ("ul", "ol"):
            return
        self.out.append(escape(data, quote=False))

    def result(self):
        while self.stack:
            t = self.stack.pop()
            if t not in ("figure", "figcaption"):
                self.out.append(f"</{t}>")
        h = "".join(self.out)
        h = re.sub(r"<(p|h2|h3|strong|em|li|blockquote)>(\s|<br>|&nbsp;| )*</\1>", "", h)  # пустые блоки
        h = re.sub(r"(<br>\s*)+</(p|h2|h3|li)>", r"</\2>", h)
        h = re.sub(r"<(ul|ol)>\s*</\1>", "", h)
        return h.strip()


def sanitize(html_in):
    p = _San()
    p.feed((html_in or "")[:MAX_BODY])
    p.close()
    return p.result()


def plain_text(h):
    return " ".join(re.sub(r"<[^>]+>", " ", h or "").split())


def from_form(form, existing, art=None):
    """→ (ошибка, dict статьи). existing — множество занятых slug (без текущей статьи)."""
    title = " ".join((form.get("title") or "").split())
    slug = (form.get("slug") or "").strip().lower() or translit(title)
    excerpt = " ".join((form.get("excerpt") or "").split())
    body = sanitize(form.get("body") or "")
    d = (form.get("date") or "").strip()
    err = None
    if not title:
        err = "Укажите заголовок."
    elif len(title) > MAX_LEN["title"]:
        err = f"Заголовок слишком длинный (максимум {MAX_LEN['title']})."
    elif len(excerpt) > MAX_LEN["excerpt"]:
        err = f"Краткое описание слишком длинное (максимум {MAX_LEN['excerpt']})."
    elif any(ord(ch) < 32 for ch in title + excerpt):
        err = "Текст содержит недопустимые символы."
    else:
        err = slug_problem(slug, existing)
    if not err:
        try:
            d = date.fromisoformat(d).isoformat()
        except ValueError:
            err = "Укажите дату публикации."
    out = dict(art or {})
    out.update(title=title, slug=slug, excerpt=excerpt, body=body, date=d)
    out.setdefault("status", "draft")
    return err, out
