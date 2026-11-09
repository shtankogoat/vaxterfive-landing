"""Генератор каталога Vaxter Five.
Читает catalog-src/catalog.json, берёт шапку и подвал из index.html,
пишет статические страницы в catalog/ и sitemap.xml.
Запуск из корня сайта:  python catalog-src/build.py
"""
import json, re, shutil, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://vaxterfive.ru"
data = json.loads((ROOT / "catalog-src/catalog.json").read_text(encoding="utf-8"))
D = data["defaults"]
index = (ROOT / "index.html").read_text(encoding="utf-8")
ver = re.search(r"style\.css\?v=(\d+)", index)
import hashlib
try:
    import rcssmin, rjsmin
    def min_css(t): return rcssmin.cssmin(t)
    def min_js(t): return rjsmin.jsmin(t)
except ImportError:  # без минификаторов просто копируем
    def min_css(t): return t
    def min_js(t): return t


def rd(rel): return (ROOT / rel).read_text(encoding="utf-8")


# --- минифицированные бандлы с хэшем в ?v= (исходники остаются для правки) ---
BUNDLES = {
    "css/style.min.css": (min_css, ["css/style.css"]),
    "css/catalog.min.css": (min_css, ["css/catalog.css"]),
    "css/constructor.min.css": (min_css, ["css/fonts-kc.css", "css/constructor.css"]),
    "js/main.min.js": (min_js, ["js/swatches.js", "js/main.js", "js/form.js"]),
    "js/contact.min.js": (min_js, ["js/contact.js"]),
    "js/catalog.min.js": (min_js, ["js/catalog.js"]),
    "js/constructor.min.js": (min_js, ["js/constructor.js"]),
}
A = {}
for dst, (fn, srcs) in BUNDLES.items():
    t = fn("\n".join(rd(x) for x in srcs))
    (ROOT / dst).write_text(t, encoding="utf-8")
    A[dst] = f"/{dst}?v={hashlib.md5(t.encode()).hexdigest()[:8]}"
V = A["css/style.min.css"].split("=")[1]
FONTS_CSS = min_css(rd("css/fonts.css"))


def head_assets(extra_css=()):
    links = "".join(f'<link rel="stylesheet" href="{A[c]}">\n' for c in ("css/style.min.css",) + tuple(extra_css))
    return ('<link rel="preload" href="/fonts/inter-tight-cyrillic.woff2" as="font" type="font/woff2" crossorigin>\n'
            f"<style>{FONTS_CSS}</style>\n{links}"
            '<link rel="icon" href="/favicon.ico" sizes="32x32">\n'
            '<link rel="icon" href="/img/favicon.svg" type="image/svg+xml">\n'
            '<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">\n'
            '<link rel="manifest" href="/site.webmanifest">\n'
            '<meta name="theme-color" content="#0b0d12">\n')


# --- WebP-копии фото товаров (jpg остаются основным форматом для админки) ---
try:
    from PIL import Image
except ImportError:
    Image = None
WIDTHS = (240, 480, 800, 1200)  # адаптивные webp: name-<w>.webp; name.webp = самый крупный


def variants(name):
    """[(w, файл)] существующих webp-вариантов по возрастанию ширины."""
    stem = (ROOT / "img/products" / name).stem
    return [(w, f"{stem}-{w}.webp") for w in WIDTHS if (ROOT / "img/products" / f"{stem}-{w}.webp").exists()]


for jpg in (ROOT / "img/products").glob("*.jp*g"):
    webp = jpg.with_suffix(".webp")
    if Image and (not webp.exists() or webp.stat().st_mtime < jpg.stat().st_mtime):
        try:
            im = Image.open(jpg).convert("RGB")
            im.save(webp, "WEBP", quality=82, method=6)
            for w in WIDTHS:
                v = jpg.with_name(f"{jpg.stem}-{w}.webp")
                if w <= im.width:
                    im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(v, "WEBP", quality=84 if w <= 480 else 82, method=6)
                elif v.exists():
                    v.unlink()
        except Exception as ex:
            print("webp skip", jpg.name, ex)

CARD_SIZES = "(max-width:1000px) 50vw, 25vw"
MAIN_SIZES = "(max-width:1000px) 100vw, 50vw"


def srcset(name, minw=0):
    v = [(w, f) for w, f in variants(name) if w >= minw]
    return ", ".join(f"/img/products/{f} {w}w" for w, f in v)


def small(name):
    v = [f for w, f in variants(name) if w >= 240]
    return v[0] if v else best(name)


def pimg(name, alt, attrs='loading="lazy" decoding="async"', sizes=CARD_SIZES, **kw):
    """<picture> с адаптивным webp (srcset) и jpg-фолбэком; width/height для CLS."""
    f = ROOT / "img/products" / name
    wh = ""
    if Image and f.exists():
        try:
            w, h = Image.open(f).size; wh = f' width="{w}" height="{h}"'
        except Exception:
            pass
    extra = "".join(f' {k}="{v}"' for k, v in kw.items())
    tag = f'<img src="/img/products/{name}" alt="{e(alt)}"{wh} {attrs}{extra}>'
    ss = srcset(name, 480)
    if ss:
        return f'<picture><source srcset="{ss}" sizes="{sizes}" type="image/webp">{tag}</picture>'
    w = f.with_suffix(".webp")
    return f'<picture><source srcset="/img/products/{w.name}" type="image/webp">{tag}</picture>' if w.exists() else tag

ORG = {
    "@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": SITE + "/#org", "name": "Vaxter Five", "legalName": "ИП Рябинин Дмитрий Анатольевич",
         "url": SITE + "/", "logo": SITE + "/img/logo.png", "email": "zakaz@vaxterfive.ru", "telephone": "+7-900-474-30-00",
         "foundingDate": "2015", "sameAs": ["https://t.me/vaxterfivebot", "https://vk.com/vaxterfive"]},
        {"@type": "ClothingStore", "@id": SITE + "/#store", "name": "Vaxter Five — пошив спортивной формы",
         "parentOrganization": {"@id": SITE + "/#org"}, "url": SITE + "/", "image": SITE + "/img/production/workshop-floor.jpg",
         "logo": SITE + "/img/logo.png", "telephone": "+7-900-474-30-00", "email": "zakaz@vaxterfive.ru",
         "address": {"@type": "PostalAddress", "streetAddress": "ул. Добросельская, д. 201", "addressLocality": "Владимир",
                     "addressRegion": "Владимирская область", "addressCountry": "RU"},
         "openingHoursSpecification": [{"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                                        "opens": "09:00", "closes": "18:00"}],
         "areaServed": "RU", "sameAs": ["https://t.me/vaxterfivebot", "https://vk.com/vaxterfive"]},
        {"@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": "Vaxter Five", "inLanguage": "ru-RU", "publisher": {"@id": SITE + "/#org"}},
    ]}


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"


def absolutize(fragment):
    fragment = re.sub(r'(src|href)="(img|css|js)/', r'\1="/\2/', fragment)
    fragment = fragment.replace('href="privacy.html"', 'href="/privacy/"')
    fragment = fragment.replace('href="#order"', 'href="#contact"').replace('href="#"', 'href="/"')
    return fragment


HEADER = absolutize(re.search(r"<header>.*?</header>", index, re.S).group(0))
FOOTER = absolutize(re.search(r"<footer.*?</footer>", index, re.S).group(0))
e = html.escape

MSG = [
    ("tg", "Telegram", "https://t.me/vaxterfivebot"),
    ("max", "MAX", "https://max.ru/id331201426687_bot"),
    ("vk", "ВКонтакте", "https://vk.com/vaxterfive"),
]


def page(title, desc, url, body, img=None, jsonld=()):
    og_img = (f'<meta property="og:image" content="{SITE}/img/products/{img}">\n'
              f'<meta name="twitter:image" content="{SITE}/img/products/{img}">') if img else ""
    lds = "\n".join(ld(x) for x in jsonld)
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE}{url}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{SITE}{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Vaxter Five">
<meta property="og:locale" content="ru_RU">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
{og_img}
{head_assets(("css/catalog.min.css",))}{lds}
</head>
<body class="cat-page">
{HEADER}
<main>
{body}
</main>
{FOOTER}
<div class="toast" id="toast">Ссылка скопирована</div>
<script src="{A['js/catalog.min.js']}" defer></script>
<script src="{A['js/contact.min.js']}" defer></script>
</body>
</html>
"""


def crumbs(*parts):
    out = ['<a href="/">Главная</a>']
    for name, href in parts:
        if href is False:  # visible but not clickable
            out.append(f'<b class="nolink">{e(name)}</b>')
        else:
            out.append(f'<a href="{href}">{e(name)}</a>' if href else f"<span>{e(name)}</span>")
    return '<nav class="crumbs mono">' + '<i>/</i>'.join(out) + "</nav>"


def fill_card(count):
    """CTA card that fills the empty slots of the last row (4 per row)."""
    rest = (4 - count % 4) % 4
    if not rest:
        return ""
    steps = "" if rest == 1 else """<ol class="pf-steps">
    <li><i>01</i><b>Присылаете идею</b><small>эскиз, фото или образец</small></li>
    <li><i>02</i><b>Делаем макет</b><small>ткань, крой, нанесение</small></li>
    <li><i>03</i><b>Шьём партию</b><small>от одной штуки, в срок</small></li>
  </ol>"""
    return f"""<a class="pcard-fill{' wide' if rest > 1 else ''}" href="#contact" style="--span:{rest}">
  <div class="pf-text">
    <span class="mono">Индивидуальный пошив</span>
    <b>Не нашли нужную модель?</b>
    <p>Сошьём по вашему эскизу или образцу — от одной штуки. Подберём ткань, крой и нанесение.</p>
    <span class="btn">Получить расчёт</span>
  </div>
  {steps}
</a>"""


def chips(active=None):
    items = [f'<a href="/catalog/" class="{"on" if active is None else ""}">Все</a>']
    for c in data["categories"]:
        items.append(f'<a href="/catalog/{c["slug"]}/" class="{"on" if active == c["slug"] else ""}">{e(c["name"])}</a>')
    return '<div class="chips">' + "".join(items) + "</div>"


def best(name):
    w = (ROOT / "img/products" / name).with_suffix(".webp")
    return w.name if w.exists() else name


def crumbs_ld(*parts):
    items = [("Главная", "/")] + list(parts)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate(items)]}


def card(c, it, h="h2", first=False, lcp=False):
    attrs = ('fetchpriority="high" decoding="async"' if lcp else 'decoding="async"') if first else 'loading="lazy" decoding="async"'
    return f"""<a class="pcard" href="/catalog/{c['slug']}/{it['slug']}/">
  <div class="pcard-ph">{pimg(it['img'][0], it['name'], attrs)}</div>
  <div class="pcard-t"><span class="mono">{e(c['name'])}</span><{h}>{e(it['name'])}</{h}><p>{e(it['short'])}</p></div>
</a>"""


def share_bar(title):
    return f"""<div class="share">
  <a class="btn" href="#contact" data-send data-note="Ссылка на изделие скопирована — вставьте её в чат с менеджером">Написать менеджеру
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a>
  <button class="btn ghost" type="button" data-copy>Скопировать ссылку
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg></button>
</div>"""


out = ROOT / "catalog"
# Очищаем содержимое catalog/, но не сам каталог: так сборке не нужны права записи в корень сайта.
if out.exists():
    for child in out.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
urls = ["/", "/catalog/"]
url_imgs = {}
import datetime
TODAY = datetime.date.today().isoformat()

# /catalog/
all_cards = "".join(
    f"""<a class="ccard" href="/catalog/{c['slug']}/{c['items'][0]['slug'] + '/' if len(c['items']) == 1 else ''}">
  <div class="ccard-ph">{pimg(c['items'][0]['img'][0], c['name'], ('fetchpriority="high" decoding="async"' if n == 0 else 'decoding="async"') if n < 4 else 'loading="lazy" decoding="async"')}</div>
  <div class="ccard-t"><h2>{e(c['name'])}</h2><span class="mono">{len(c['items'])} поз.</span></div>
</a>"""
    for n, c in enumerate(data["categories"])
)
body = f"""<section class="cat-hero"><div class="wrap">
  {crumbs(("Каталог", None))}
  <h1>Каталог продукции</h1>
</div></section>
<section class="cat-body"><div class="wrap"><div class="ccards">{all_cards}</div></div></section>
"""
out.mkdir(parents=True, exist_ok=True)
(out / "index.html").write_text(page("Каталог продукции — Vaxter Five", "Каталог спортивной одежды Vaxter Five: футболки, командная форма, худи, куртки, шорты, единоборства. Пошив от 1 штуки во Владимире.", "/catalog/", body, jsonld=[
    crumbs_ld(("Каталог", "/catalog/")),
    {"@context": "https://schema.org", "@type": "ItemList", "name": "Каталог продукции Vaxter Five", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": c["name"], "url": f"{SITE}/catalog/{c['slug']}/"} for i, c in enumerate(data["categories"])]}]), encoding="utf-8")

PER_PAGE = 40  # 10 рядов по 4 карточки


def pager(curl, n, total):
    if total <= 1:
        return ""
    href = lambda k: curl if k == 1 else f"{curl}page/{k}/"
    arrow = lambda k, sym, lbl: (f'<a class="pg-arr" href="{href(k)}" rel="{"prev" if sym == "←" else "next"}" aria-label="{lbl}">{sym}</a>'
                                 if 1 <= k <= total else f'<span class="pg-arr off" aria-hidden="true">{sym}</span>')
    nums = "".join(f'<span class="on" aria-current="page">{k}</span>' if k == n else f'<a href="{href(k)}">{k}</a>'
                   for k in range(1, total + 1))
    return f'<nav class="pager" aria-label="Страницы">{arrow(n - 1, "←", "Предыдущая")}{nums}{arrow(n + 1, "→", "Следующая")}</nav>'


for c in data["categories"]:
    curl = f"/catalog/{c['slug']}/"
    items = c["items"]
    total = max(1, -(-len(items) // PER_PAGE))
    single = len(items) == 1
    if single:  # one product -> category URL forwards straight to it
        target = f"{curl}{items[0]['slug']}/"
        (out / c["slug"]).mkdir(parents=True, exist_ok=True)
        (out / c["slug"] / "index.html").write_text(
            f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>{e(c["name"])} | Vaxter Five</title>'
            f'<meta name="robots" content="noindex"><link rel="canonical" href="{SITE}{target}">'
            f'<meta http-equiv="refresh" content="0;url={target}"><script>location.replace("{target}")</script></head>'
            f'<body><a href="{target}">{e(items[0]["name"])}</a></body></html>', encoding="utf-8")
    for n in range(1, 0 if single else total + 1):
        purl_page = curl if n == 1 else f"{curl}page/{n}/"
        urls.append(purl_page)
        chunk = items[(n - 1) * PER_PAGE: n * PER_PAGE]
        suffix = f" — страница {n}" if n > 1 else ""
        body = f"""<section class="cat-hero"><div class="wrap">
  {crumbs(("Каталог", "/catalog/"), (c["name"], None))}
  <h1>{e(c["name"])}</h1>
  <p class="cat-lead">{e(c["lead_text"])}</p>
</div></section>
<section class="cat-body"><div class="wrap"><div class="pcards">{"".join(card(c, it, "h2", n == 1 and i < 2, n == 1 and i == 0) for i, it in enumerate(chunk))}{fill_card(len(chunk))}</div>{pager(curl, n, total)}</div></section>"""
        d = out / c["slug"] if n == 1 else out / c["slug"] / "page" / str(n)
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page(f"{c['name']} на заказ от 1 штуки — пошив во Владимире{suffix} | Vaxter Five", c["lead_text"], purl_page, body, chunk[0]["img"][0], jsonld=[
            crumbs_ld(("Каталог", "/catalog/"), (c["name"], curl)),
            {"@context": "https://schema.org", "@type": "ItemList", "name": c["name"] + suffix, "itemListElement": [
                {"@type": "ListItem", "position": (n - 1) * PER_PAGE + i + 1, "name": x["name"], "url": f"{SITE}{curl}{x['slug']}/"} for i, x in enumerate(chunk)]}]), encoding="utf-8")

    for it in c["items"]:
        purl = f"{curl}{it['slug']}/"
        urls.append(purl)
        url_imgs[purl] = [(f"/img/products/{best(im)}", it["name"]) for im in it["img"]]
        spec = lambda k: it.get(k, D.get(k, ""))
        thumbs = "".join(
            f'<button type="button" class="{"on" if i == 0 else ""}" data-img="/img/products/{best(im)}" data-srcset="{srcset(im, 480)}" aria-label="Фото {i + 1}"><img src="/img/products/{small(im)}" alt="{e(it['name'])} — фото {i + 1}" width="240" height="320" loading="lazy" decoding="async"></button>'
            for i, im in enumerate(it["img"])
        ) if len(it["img"]) > 1 else ""
        rows = [("Материал", spec("fabric")), ("Нанесение", spec("print")), ("Размеры", spec("sizes")),
                ("Минимальный заказ", spec("min")), ("Сроки", spec("lead"))]
        specs = "".join(f"<div><dt>{k}</dt><dd>{e(v)}</dd></div>" for k, v in rows if v)
        msg = "".join(f'<a class="mbtn {k}" href="{u}" target="_blank" rel="noopener">{n}</a>' for k, n, u in MSG)
        others = [x for x in c["items"] if x is not it]
        more = f"""<section class="cat-more"><div class="wrap"><h2>Ещё в разделе «{e(c['name'])}»</h2>
<div class="pcards">{"".join(card(c, x, "h3") for x in others)}</div></div></section>""" if others else ""
        body = f"""<section class="prod"><div class="wrap">
  {crumbs(("Каталог", "/catalog/"), (c["name"], False if single else curl), (it["name"], None))}
  <div class="prod-grid">
    <div class="gallery">
      <div class="gallery-main"><img id="gmain" src="/img/products/{best(it['img'][0])}" srcset="{srcset(it['img'][0], 480)}" sizes="{MAIN_SIZES}" alt="{e(it['name'])}" width="1200" height="1600" fetchpriority="high"></div>
      <div class="gallery-thumbs">{thumbs}</div>
    </div>
    <div class="prod-info">
      <span class="mono">{e(c['name'])}</span>
      <h1>{e(it['name'])}</h1>
      <p class="prod-short">{e(it['short'])}</p>
      <dl class="pspecs">{specs}</dl>
      {share_bar(it['name'] + " — Vaxter Five")}
    </div>
  </div>
</div></section>
{more}"""
        (out / c["slug"] / it["slug"]).mkdir(parents=True, exist_ok=True)
        (out / c["slug"] / it["slug"] / "index.html").write_text(
            page(f"{it['name']} на заказ — пошив от 1 штуки | Vaxter Five",
                 f"{it['short'].rstrip('.')}. Пошив на заказ во Владимире от 1 штуки, нанесение логотипа и номеров. Собственное производство Vaxter Five.", purl, body, it["img"][0], jsonld=[
                crumbs_ld(("Каталог", "/catalog/"), (c["name"], curl), (it["name"], purl)),
                {"@context": "https://schema.org", "@type": "Product", "name": it["name"], "description": it["short"],
                 "image": [f"{SITE}/img/products/{im}" for im in it["img"]], "category": c["name"], "url": SITE + purl,
                 "brand": {"@type": "Brand", "name": "Vaxter Five"}, "manufacturer": {"@id": SITE + "/#org"}}]), encoding="utf-8")

# --- блог /articles/ (отдельный модуль catalog-src/articles.py; добавляет свои URL в sitemap) ---
import articles as _articles  # noqa: E402
_articles.build(globals())

def sm_url(u):
    depth = u.strip("/").count("/") + (1 if u.strip("/") else 0)
    prio = {0: "1.0", 1: "0.9", 2: "0.8"}.get(depth, "0.7")
    imgs = "".join(f"<image:image><image:loc>{SITE}{src}</image:loc><image:title>{e(t)}</image:title></image:image>"
                   for src, t in url_imgs.get(u, []))
    return f"  <url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod><priority>{prio}</priority>{imgs}</url>\n"


url_imgs.setdefault("/", [("/img/hero/team-10-years.webp", "Команда Vaxter Five"),
                          ("/img/production/workshop-floor.webp", "Швейное производство Vaxter Five во Владимире")])
(ROOT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
    + "".join(sm_url(u) for u in urls) + "</urlset>\n", encoding="utf-8")
print(f"OK: {len(urls) - 1} catalog pages + sitemap.xml")


# --- sync header/footer into other static pages (one source: index.html) ---
for rel in ["privacy/index.html"]:
    f = ROOT / rel
    if not f.exists():
        continue
    t = f.read_text(encoding="utf-8")
    t = re.sub(r"<header>.*?</header>", lambda m: HEADER, t, count=1, flags=re.S)
    t = re.sub(r"<footer.*?</footer>", lambda m: FOOTER, t, count=1, flags=re.S)
    if "<!--head-assets-->" not in t:  # одноразовая миграция со старых <link>
        t = re.sub(r'<link rel="(preconnect|icon|apple-touch-icon|stylesheet)"[^>]*>\s*|<link href="https://fonts[^>]*>\s*', "", t)
        t = t.replace("</head>", "<!--head-assets--><!--/head-assets-->\n</head>", 1)
    if '<link rel="canonical"' not in t:
        t = t.replace("<!--head-assets-->", f'<link rel="canonical" href="{SITE}/privacy/">\n<!--head-assets-->', 1)
    t = re.sub(r'<script src="/js/contact[^"]*" defer></script>', f'<script src="{A["js/contact.min.js"]}" defer></script>', t)
    if "/js/contact" not in t:
        t = t.replace("</body>", f'<script src="{A["js/contact.min.js"]}" defer></script>\n</body>', 1)
    t = re.sub(r"<!--head-assets-->.*?<!--/head-assets-->", lambda m: "<!--head-assets-->\n" + head_assets() + "<!--/head-assets-->", t, flags=re.S)
    f.write_text(t, encoding="utf-8")
print("synced header/footer: privacy")

# --- главная: ассеты, JSON-LD, скрипты (разметка правится в index.html вручную) ---
t = (ROOT / "index.html").read_text(encoding="utf-8")
t = re.sub(r"<!--head-assets-->.*?<!--/head-assets-->", lambda m: "<!--head-assets-->\n" + head_assets()
           + f'<meta name="kc-assets" content="{A["css/constructor.min.css"]}|{A["js/constructor.min.js"]}">\n<!--/head-assets-->', t, flags=re.S)
t = re.sub(r"<!--jsonld-->.*?<!--/jsonld-->", lambda m: "<!--jsonld-->" + ld(ORG) + "<!--/jsonld-->", t, flags=re.S)
t = re.sub(r"<!--scripts-->.*?<!--/scripts-->", lambda m: "<!--scripts-->\n" + "".join(
    f'<script src="{A[j]}" defer></script>\n' for j in ("js/main.min.js", "js/contact.min.js")) + "<!--/scripts-->", t, flags=re.S)
(ROOT / "index.html").write_text(t, encoding="utf-8")
print("index.html: assets synced")

# --- custom error pages (nginx error_page → /errors/<code>.html) ---
ERRORS = {
    404: ("Страница не найдена", "Похоже, ссылка устарела или в адресе опечатка. Зато всё остальное на месте — загляните в каталог или соберите свою форму."),
    403: ("Доступ закрыт", "У этой страницы ограниченный доступ. Вернитесь на главную — там всё самое интересное."),
    500: ("Что-то пошло не так", "На сервере произошла ошибка. Мы уже разбираемся — попробуйте обновить страницу через минуту."),
    502: ("Сервер перезагружается", "Сайт обновляется и вернётся через минуту. Попробуйте обновить страницу."),
    503: ("Технические работы", "Мы ненадолго закрылись на обслуживание. Вернёмся совсем скоро."),
    504: ("Сервер долго отвечает", "Запрос занял слишком много времени. Попробуйте обновить страницу."),
}
(ROOT / "errors").mkdir(exist_ok=True)
for code, (title, text) in ERRORS.items():
    body = f"""<section class="err"><div class="wrap err-wrap">
  <div class="err-code" aria-hidden="true">{code}</div>
  <div class="err-txt"><h1>{e(title)}</h1>
  <p>{e(text)}</p></div>
  <div class="err-btns">
    <a class="btn" href="/">На главную</a>
    <a class="btn ghost" href="/catalog/">Каталог</a>
    <a class="btn ghost" href="#contact">Написать нам</a>
  </div>
</div></section>"""
    html_ = page(f"{title} — Vaxter Five", text, "/", body).replace('<link rel="canonical"', '<meta name="robots" content="noindex"><link rel="canonical"')
    (ROOT / "errors" / f"{code}.html").write_text(html_, encoding="utf-8")
print("error pages:", ", ".join(map(str, ERRORS)))
