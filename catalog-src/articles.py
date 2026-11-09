"""Блог Vaxter Five: /articles/ (список с пагинацией) и /articles/<slug>/.
Вызывается из build.py: articles.build(globals()) — до записи sitemap.xml.
Данные — catalog.json → "articles" (только status == "published"). HTML тела уже очищен админкой."""
import hashlib, json, re, shutil
from datetime import date
from pathlib import Path

PER_PAGE = 40
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
IMG_RE = re.compile(r"^/img/articles/a-[0-9a-f]{16}\.webp$")


def ru_date(iso):
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return ""
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def build(B):
    ROOT, SITE, e, page, ld, crumbs, crumbs_ld, pager = (B[k] for k in (
        "ROOT", "SITE", "e", "page", "ld", "crumbs", "crumbs_ld", "pager"))
    data, urls, url_imgs, A, min_css = B["data"], B["urls"], B["url_imgs"], B["A"], B["min_css"]
    try:
        from PIL import Image
    except ImportError:
        Image = None

    # --- css/articles.min.css с хэшем ---
    css = min_css((ROOT / "css/articles.css").read_text(encoding="utf-8"))
    (ROOT / "css/articles.min.css").write_text(css, encoding="utf-8")
    A["css/articles.min.css"] = f"/css/articles.min.css?v={hashlib.md5(css.encode()).hexdigest()[:8]}"
    css_link = f'<link rel="stylesheet" href="{A["css/articles.min.css"]}">\n'

    def size(url):
        f = ROOT / url.lstrip("/")
        if Image and f.is_file():
            try:
                with Image.open(f) as im:
                    return im.size
            except Exception:
                pass
        return None

    def small(url):
        s = url[:-5] + "-800.webp"
        return s if (ROOT / s.lstrip("/")).is_file() else None

    def img(url, alt, attrs='loading="lazy" decoding="async"', sizes="(max-width:640px) 100vw, (max-width:1000px) 50vw, 33vw"):
        wh = size(url)
        sm = small(url)
        ss = f' srcset="{sm} 800w, {url} {wh[0]}w" sizes="{sizes}"' if sm and wh else ""
        whs = f' width="{wh[0]}" height="{wh[1]}"' if wh else ""
        return f'<img src="{url}"{ss} alt="{e(alt)}"{whs} {attrs}>'

    def enhance(body):
        """Картинки тела: размеры (CLS), srcset, lazy. Остальная разметка — как сохранила админка."""
        def rep(m):
            src, alt = m.group(1), m.group(2)
            if not IMG_RE.match(src):
                return ""
            return img(src, alt, sizes="(max-width:820px) 100vw, 760px")
        return re.sub(r'<img src="([^"]+)" alt="([^"]*)">', rep, body)

    def excerpt(a):
        if a.get("excerpt"):
            return a["excerpt"]
        t = " ".join(re.sub(r"<[^>]+>", " ", a.get("body", "")).split())
        t = re.sub(r"&[a-z]+;|&#\d+;", lambda m: {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&nbsp;": " "}.get(m.group(0), " "), t)
        return (t[:157].rsplit(" ", 1)[0] + "…") if len(t) > 160 else t

    def finish(htm, og_img=None, art=None):
        extra = css_link
        if og_img:
            extra += (f'<meta property="og:image" content="{SITE}{og_img}">\n'
                      f'<meta name="twitter:image" content="{SITE}{og_img}">\n')
        if art:
            htm = htm.replace('<meta property="og:type" content="website">', '<meta property="og:type" content="article">', 1)
            extra += f'<meta property="article:published_time" content="{art["date"]}">\n'
            if art.get("updated"):
                extra += f'<meta property="article:modified_time" content="{art["updated"]}">\n'
        htm = htm.replace('<body class="cat-page">', '<body class="cat-page art-page">', 1)
        return htm.replace("</head>", extra + "</head>", 1)

    items = []
    seen = set()
    for a in data.get("articles", []):
        if a.get("status") != "published" or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", a.get("slug", "")) \
                or a["slug"] == "page" or a["slug"] in seen or not a.get("title"):
            continue
        seen.add(a["slug"])
        if a.get("cover") and not IMG_RE.match(a["cover"]):
            a = {**a, "cover": None}
        items.append(a)
    items.sort(key=lambda a: (a.get("date", ""), a.get("created", "")), reverse=True)

    out = ROOT / "articles"
    if out.exists():
        for child in out.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    out.mkdir(parents=True, exist_ok=True)

    def card(a, lcp=False):
        ph = (img(a["cover"], a["title"], 'fetchpriority="high" decoding="async"' if lcp else 'loading="lazy" decoding="async"')
              if a.get("cover") else '<span class="acard-noimg" aria-hidden="true">V5</span>')
        return f"""<a class="acard" href="/articles/{a['slug']}/">
  <div class="acard-ph">{ph}</div>
  <div class="acard-t"><time class="mono" datetime="{a['date']}">{ru_date(a['date'])}</time><h2>{e(a['title'])}</h2><p>{e(excerpt(a))}</p>
  <span class="acard-more">Читать <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span></div>
</a>"""

    # --- список ---
    total = max(1, -(-len(items) // PER_PAGE))
    lead = "Полезное о спортивной форме: ткани, нанесение, размеры, сроки и уход. Пишем из опыта собственного производства во Владимире."
    for n in range(1, total + 1):
        purl = "/articles/" if n == 1 else f"/articles/page/{n}/"
        urls.append(purl)
        chunk = items[(n - 1) * PER_PAGE: n * PER_PAGE]
        suffix = f" — страница {n}" if n > 1 else ""
        cards = "".join(card(a, n == 1 and i == 0) for i, a in enumerate(chunk))
        rest = (4 - len(chunk) % 4) % 4 if n == total else 0
        tail = (f'<a class="pcard-fill{" wide" if rest > 1 else ""}" href="#contact" style="--span:{rest}"><div class="pf-text">'
                '<span class="mono">Новые статьи — 1–2 в месяц</span><b>Есть вопрос о форме?</b>'
                '<p>Ткани, нанесение, размеры, сроки — ответим лично и подготовим расчёт под вашу команду.</p>'
                '<span class="btn">Напишите нам</span></div>'
                + ('<ol class="pf-steps"><li><i>01</i><b>Ткани</b><small>что выбрать под вид спорта</small></li>'
                   '<li><i>02</i><b>Нанесение</b><small>сублимация, термоперенос, вышивка</small></li>'
                   '<li><i>03</i><b>Сроки</b><small>от макета до готовой партии</small></li></ol>' if rest > 1 else '')
                + '</a>') if rest else ""
        grid = f'<div class="acards">{cards}{tail}</div>' if chunk else \
            '<div class="aempty"><b>Скоро здесь появятся статьи</b><p>А пока загляните в каталог — там вся наша продукция.</p><a class="btn" href="/catalog/">Открыть каталог</a></div>'
        body = f"""<section class="cat-hero"><div class="wrap">
  {crumbs(("Статьи", None))}
  <div class="cat-head"><h1>Статьи</h1></div>
</div></section>
<section class="cat-body"><div class="wrap">{grid}{pager("/articles/", n, total)}</div></section>"""
        d = out if n == 1 else out / "page" / str(n)
        d.mkdir(parents=True, exist_ok=True)
        htm = page(f"Статьи о спортивной форме и пошиве{suffix} | Vaxter Five", lead, purl, body, jsonld=[
            crumbs_ld(("Статьи", "/articles/")),
            {"@context": "https://schema.org", "@type": "Blog", "name": "Статьи Vaxter Five", "url": SITE + "/articles/",
             "publisher": {"@id": SITE + "/#org"}, "blogPost": [
                {"@type": "BlogPosting", "headline": a["title"], "url": f"{SITE}/articles/{a['slug']}/", "datePublished": a["date"]}
                for a in chunk]}])
        (d / "index.html").write_text(finish(htm, chunk[0].get("cover") if chunk and chunk[0].get("cover") else None), encoding="utf-8")
        if chunk and chunk[0].get("cover"):
            url_imgs[purl] = [(chunk[0]["cover"], chunk[0]["title"])]

    # --- статьи ---
    for a in items:
        purl = f"/articles/{a['slug']}/"
        urls.append(purl)
        body_html = enhance(a.get("body", ""))
        imgs = ([(a["cover"], a["title"])] if a.get("cover") else []) + \
            [(m.group(1), m.group(2) or a["title"]) for m in re.finditer(r'<img src="(/img/articles/[^"]+)" alt="([^"]*)">', a.get("body", ""))]
        url_imgs[purl] = imgs
        hi = 'fetchpriority="high" decoding="async"'
        cover = f'<figure class="art-cover">{img(a["cover"], a["title"], hi, "(max-width:1400px) 100vw, 1400px")}</figure>' if a.get("cover") else ""
        others = [x for x in items if x is not a][:3]
        more = f"""<section class="cat-more art-more"><div class="wrap"><h2>Другие статьи</h2>
<div class="acards">{"".join(card(x) for x in others)}</div></div></section>""" if others else ""
        upd = f' · обновлено {ru_date(a["updated"])}' if a.get("updated") and a["updated"] != a["date"] else ""
        desc = excerpt(a)
        body = f"""<article class="art">
<section class="art-hero"><div class="wrap">
  {crumbs(("Статьи", "/articles/"), (a["title"], None))}
  <time class="mono" datetime="{a['date']}">{ru_date(a['date'])}{upd}</time>
  <h1>{e(a['title'])}</h1>
  {f'<p class="art-lead">{e(a["excerpt"])}</p>' if a.get("excerpt") else ""}
  {cover}
</div></section>
<section class="art-body"><div class="wrap"><div class="art-text">{body_html}</div>
  <aside class="art-cta"><span class="mono">Индивидуальный пошив</span><b>Нужна форма для команды?</b>
    <p>Сошьём по вашему эскизу или образцу — от одной штуки. Подберём ткань, крой и нанесение.</p>
    <div class="art-cta-btns"><a class="btn" href="#contact">Получить расчёт</a><a class="btn ghost" href="/catalog/">Каталог</a></div></aside>
</div></section>
</article>
{more}"""
        (out / a["slug"]).mkdir(parents=True, exist_ok=True)
        ld_art = {"@context": "https://schema.org", "@type": "Article", "headline": a["title"][:110], "description": desc,
                  "datePublished": a["date"], "dateModified": a.get("updated") or a["date"], "inLanguage": "ru-RU",
                  "mainEntityOfPage": {"@type": "WebPage", "@id": SITE + purl}, "url": SITE + purl,
                  "author": {"@type": "Organization", "name": "Vaxter Five", "url": SITE + "/"},
                  "publisher": {"@id": SITE + "/#org"}}
        if imgs:
            ld_art["image"] = [SITE + u for u, _ in imgs]
        htm = page(f"{a['title']} | Vaxter Five", desc, purl, body, jsonld=[
            crumbs_ld(("Статьи", "/articles/"), (a["title"], purl)), ld_art])
        (out / a["slug"] / "index.html").write_text(finish(htm, a.get("cover") or (imgs[0][0] if imgs else None), a), encoding="utf-8")
    print(f"articles: {len(items)} published, {total} list page(s)")
