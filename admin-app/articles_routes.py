"""Раздел «Статьи» админки. Подключается из app.py: articles_routes.register(app, ns).
Хранение — ключ "articles" в catalog.json; каждое сохранение = save_and_publish (как у каталога)."""
from datetime import date

from flask import abort, flash, jsonify, redirect, render_template, request, url_for

import articles_admin as AA
import store as S


def register(app, ns):
    P, login_required, save_and_publish, log = ns["P"], ns["login_required"], ns["save_and_publish"], ns["log"]

    def arts(data):
        return data.setdefault("articles", [])

    def get_art(data, slug):
        for a in arts(data):
            if a.get("slug") == slug:
                return a
        abort(404)

    def published_url(a):
        return f"/articles/{a['slug']}/" if a.get("status") == "published" else None

    @app.get(P + "/articles")
    @login_required
    def articles():
        items = sorted(arts(S.load_draft()), key=lambda a: a.get("date", ""), reverse=True)
        return render_template("articles.html", items=items)

    def save_form(data, a=None):
        taken = {x.get("slug") for x in arts(data) if x is not a}
        err, new = AA.from_form(request.form, taken, a)
        cover = request.files.get("cover")
        if not err and cover and cover.filename:
            try:
                new["cover"] = AA.process_image(cover)[0]
            except ValueError as e:
                err = "Обложка: " + str(e)
        if not err and request.form.get("cover_remove") == "1":
            new.pop("cover", None)
        if not err and request.form.get("status") in ("draft", "published"):
            new["status"] = request.form["status"]
        if not err and new["status"] == "published" and not AA.plain_text(new["body"]):
            err = "Нельзя опубликовать пустую статью — добавьте текст или сохраните как черновик."
        return err, new

    @app.route(P + "/articles/new", methods=["GET", "POST"])
    @login_required
    def article_new():
        if request.method == "POST":
            data = S.load_draft()
            err, new = save_form(data)
            if err:
                flash(err, "error")
                return render_template("article.html", a=None, form=new)
            new["created"] = date.today().isoformat()
            arts(data).append(new)
            pub = save_and_publish(data)
            log("Создана статья", f"{new['slug']} «{new['title']}» ({new['status']})")
            if pub:
                flash("Статья сохранена" + (" и опубликована на сайте." if new["status"] == "published" else " как черновик."), "ok")
            return redirect(url_for("article", slug=new["slug"]))
        return render_template("article.html", a=None, form={"date": date.today().isoformat(), "status": "draft"})

    @app.route(P + "/articles/<slug>", methods=["GET", "POST"])
    @login_required
    def article(slug):
        data = S.load_draft()
        a = get_art(data, slug)
        if request.method == "POST":
            err, new = save_form(data, a)
            if err:
                flash(err, "error")
                return render_template("article.html", a=a, form=new, live=published_url(a))
            new["updated"] = date.today().isoformat()
            a.clear()
            a.update(new)
            pub = save_and_publish(data)
            log("Изменена статья", f"{slug} → {new['slug']} ({new['status']})")
            if pub:
                flash("Сохранено" + (" и опубликовано на сайте." if new["status"] == "published" else " (черновик, на сайте не виден)."), "ok")
            return redirect(url_for("article", slug=new["slug"]))
        return render_template("article.html", a=a, form=a, live=published_url(a))

    @app.post(P + "/articles/<slug>/status")
    @login_required
    def article_status(slug):
        data = S.load_draft()
        a = get_art(data, slug)
        to = "draft" if a.get("status") == "published" else "published"
        if to == "published" and not AA.plain_text(a.get("body", "")):
            flash("Нельзя опубликовать пустую статью.", "error")
            return redirect(url_for("articles"))
        a["status"] = to
        pub = save_and_publish(data)
        log("Статья опубликована" if to == "published" else "Статья снята в черновик", slug)
        if pub:
            flash(f"«{a['title']}» " + ("опубликована на сайте." if to == "published" else "снята с сайта (черновик)."), "ok")
        return redirect(request.form.get("back") == "edit" and url_for("article", slug=slug) or url_for("articles"))

    @app.post(P + "/articles/<slug>/delete")
    @login_required
    def article_delete(slug):
        data = S.load_draft()
        a = get_art(data, slug)
        arts(data).remove(a)
        save_and_publish(data)  # файлы картинок не удаляем: нужны для восстановления старых версий
        log("Удалена статья", f"{slug} «{a.get('title', '')}»")
        flash(f"Статья «{a.get('title', '')}» удалена.", "ok")
        return redirect(url_for("articles"))

    @app.post(P + "/articles/upload")
    @login_required
    def article_upload():
        f = request.files.get("image")
        if not f or not f.filename:
            return jsonify(ok=False, error="Файл не выбран."), 400
        try:
            url, w, h = AA.process_image(f)
        except ValueError as e:
            return jsonify(ok=False, error=str(e)), 400
        log("Загружено фото статьи", url)
        return jsonify(ok=True, url=url, w=w, h=h)
