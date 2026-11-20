"""Раздел «Образцы» админки — лента образцов (ткани, фурнитура, нанесение) на главной.
Хранение — ключ "swatches" в catalog.json; build.py генерирует из него js/swatches.js.
Каждое сохранение = save_and_publish (как у каталога и статей)."""
from flask import abort, flash, redirect, render_template, request, url_for

import articles_admin as AA
import store as S

TYPES = ["Ткань", "Фурнитура", "Нанесение"]
LIM = {"t": 40, "n": 60, "d": 400}


def register(app, ns):
    P, login_required, save_and_publish, log = ns["P"], ns["login_required"], ns["save_and_publish"], ns["log"]

    def sws(data):
        return data.setdefault("swatches", [])

    def get(data, i):
        lst = sws(data)
        if not 0 <= i < len(lst):
            abort(404)
        return lst[i]

    def from_form(old=None):
        f = {k: " ".join((request.form.get(k) or "").split()) if k != "d" else (request.form.get(k) or "").strip() for k in LIM}
        new = dict(old or {})
        new.update(f)
        if not f["n"]:
            return "Укажите название.", new
        if not f["t"]:
            return "Укажите тип (например, Ткань).", new
        for k, m in LIM.items():
            if len(f[k]) > m:
                return f"Слишком длинный текст (максимум {m} символов).", new
        photo = request.files.get("photo")
        if photo and photo.filename:
            try:
                new["img"] = AA.process_image(photo, max_side=900)[0]
            except ValueError as e:
                return "Фото: " + str(e), new
        if not new.get("img"):
            return "Загрузите фото образца.", new
        return None, new

    @app.get(P + "/swatches")
    @login_required
    def swatches():
        return render_template("swatches.html", items=list(enumerate(sws(S.load_draft()))))

    @app.route(P + "/swatches/new", methods=["GET", "POST"])
    @login_required
    def swatch_new():
        if request.method == "POST":
            data = S.load_draft()
            err, new = from_form()
            if err:
                flash(err, "error")
                return render_template("swatch.html", i=None, form=new, types=TYPES)
            sws(data).append(new)
            if save_and_publish(data):
                flash(f"Образец «{new['n']}» добавлен на сайт.", "ok")
            log("Добавлен образец", new["n"])
            return redirect(url_for("swatches"))
        return render_template("swatch.html", i=None, form={"t": TYPES[0]}, types=TYPES)

    @app.route(P + "/swatches/<int:i>", methods=["GET", "POST"])
    @login_required
    def swatch(i):
        data = S.load_draft()
        s = get(data, i)
        if request.method == "POST":
            err, new = from_form(s)
            if err:
                flash(err, "error")
                return render_template("swatch.html", i=i, form=new, types=TYPES)
            s.clear()
            s.update(new)
            if save_and_publish(data):
                flash("Сохранено и опубликовано на сайте.", "ok")
            log("Изменён образец", new["n"])
            return redirect(url_for("swatches"))
        return render_template("swatch.html", i=i, form=s, types=TYPES)

    @app.post(P + "/swatches/<int:i>/move")
    @login_required
    def swatch_move(i):
        data = S.load_draft()
        lst = sws(data)
        get(data, i)
        j = i + (1 if request.form.get("d") == "down" else -1)
        if 0 <= j < len(lst):
            lst[i], lst[j] = lst[j], lst[i]
            save_and_publish(data)
            log("Порядок образцов", lst[j].get("n", ""))
        return redirect(url_for("swatches"))

    @app.post(P + "/swatches/<int:i>/delete")
    @login_required
    def swatch_delete(i):
        data = S.load_draft()
        s = get(data, i)
        sws(data).remove(s)
        save_and_publish(data)  # файл фото не удаляем — нужен для восстановления версий
        log("Удалён образец", s.get("n", ""))
        flash(f"Образец «{s.get('n', '')}» удалён.", "ok")
        return redirect(url_for("swatches"))
