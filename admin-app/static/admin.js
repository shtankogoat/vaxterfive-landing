// Без inline-скриптов (CSP script-src 'self'). Никаких window.confirm/alert/prompt — только свои окна.
(function () {
  "use strict";

  // ---------- модальное окно подтверждения ----------
  var modal, lastFocus, onOk;
  function buildModal() {
    modal = document.createElement("div");
    modal.className = "modal";
    modal.hidden = true;
    modal.innerHTML =
      '<div class="modal-bg" data-close></div>' +
      '<div class="modal-box" role="alertdialog" aria-modal="true" aria-labelledby="m-title" aria-describedby="m-text">' +
      '<div class="modal-ico" aria-hidden="true">!</div>' +
      '<h2 id="m-title">Подтвердите действие</h2>' +
      '<p id="m-text"></p>' +
      '<div class="modal-act"><button type="button" class="btn ghost" data-close>Отмена</button>' +
      '<button type="button" class="btn danger" data-ok>Да, продолжить</button></div></div>';
    document.body.appendChild(modal);
    modal.addEventListener("click", function (e) {
      if (e.target.closest("[data-close]")) close();
      else if (e.target.closest("[data-ok]")) { var f = onOk; close(); if (f) f(); }
    });
    modal.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { e.preventDefault(); close(); }
      if (e.key === "Tab") { // ловушка фокуса
        var els = modal.querySelectorAll("button"), first = els[0], last = els[els.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }
  function open(text, okLabel, danger, cb) {
    if (!modal) buildModal();
    lastFocus = document.activeElement;
    modal.querySelector("#m-text").textContent = text;
    var ok = modal.querySelector("[data-ok]");
    ok.textContent = okLabel || "Да, продолжить";
    ok.classList.toggle("danger", !!danger);
    onOk = cb;
    modal.hidden = false;
    document.body.classList.add("modal-open");
    requestAnimationFrame(function () { modal.classList.add("on"); modal.querySelector("[data-close].btn").focus(); });
  }
  function close() {
    if (!modal || modal.hidden) return;
    modal.classList.remove("on");
    modal.hidden = true;
    document.body.classList.remove("modal-open");
    onOk = null;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener("submit", function (e) {
    var f = e.target;
    var q = f.getAttribute("data-confirm");
    if (q && !f.__confirmed) {
      e.preventDefault();
      var danger = /удал|сброс|отмен|выйти/i.test(q + (f.action || ""));
      var label = /выйти/i.test(q) ? "Выйти" : /удал/i.test(q) ? "Удалить" : /сброс/i.test(q) ? "Сбросить" : /вернуть/i.test(q) ? "Вернуть" : /выйти/i.test(q) ? "Выйти" : "Да";
      open(q, label, danger, function () { f.__confirmed = true; if (f.requestSubmit) f.requestSubmit(); else f.submit(); });
      return;
    }
    f.__confirmed = false;
    var busy = f.getAttribute("data-busy");
    if (busy) {
      var b = f.querySelector("button.btn"); if (b) { b.textContent = busy; b.classList.add("loading"); }
      document.body.classList.add("busy");
    }
  });

  // ---------- slug из названия ----------
  var src = document.querySelector("[data-slug-src]"), dst = document.querySelector("[data-slug]");
  if (src && dst) {
    var map = {а:"a",б:"b",в:"v",г:"g",д:"d",е:"e",ё:"e",ж:"zh",з:"z",и:"i",й:"y",к:"k",л:"l",м:"m",н:"n",о:"o",п:"p",р:"r",с:"s",т:"t",у:"u",ф:"f",х:"h",ц:"ts",ч:"ch",ш:"sh",щ:"sch",ъ:"",ы:"y",ь:"",э:"e",ю:"yu",я:"ya"};
    var touched = dst.value !== "";
    dst.addEventListener("input", function () { touched = true; });
    src.addEventListener("input", function () {
      if (touched) return;
      dst.value = src.value.toLowerCase().split("").map(function (ch) { return map[ch] !== undefined ? map[ch] : ch; })
        .join("").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
    });
  }

  // ---------- выбор области фото (4:5, как карточка на сайте) ----------
  var RATIO = 4 / 5;
  function defCrop(W, H) {
    var w = W, h = w / RATIO;
    if (h > H) { h = H; w = h * RATIO; }
    return { x: (W - w) / 2 / W, y: (H - h) / 2 / H, w: w / W, h: h / H };
  }
  function cropper(src, start, done) {
    var ov = document.createElement("div");
    ov.className = "crop-ov";
    ov.innerHTML = '<div class="crop-box"><div class="crop-head"><b>Выберите область</b><small>Перетащите рамку, угол — размер. Формат 4:5, как в карточке товара.</small></div>' +
      '<div class="crop-stage"><img alt=""><div class="crop-fr"><i class="crop-h"></i></div></div>' +
      '<div class="crop-act"><button type="button" class="btn ghost" data-a="full">Всё фото</button><span></span><button type="button" class="btn ghost" data-a="no">Отмена</button><button type="button" class="btn" data-a="ok">Готово</button></div></div>';
    document.body.appendChild(ov);
    var img = ov.querySelector("img"), fr = ov.querySelector(".crop-fr"), c;
    function W() { return img.clientWidth; } function H() { return img.clientHeight; }
    function draw() {
      fr.style.left = c.x * W() + "px"; fr.style.top = c.y * H() + "px";
      fr.style.width = c.w * W() + "px"; fr.style.height = c.h * H() + "px";
    }
    img.onload = function () {
      c = start ? { x: start.x, y: start.y, w: start.w, h: start.h } : defCrop(img.naturalWidth, img.naturalHeight);
      draw();
    };
    img.src = src;
    var drag = null;
    fr.addEventListener("pointerdown", function (e) {
      e.preventDefault(); fr.setPointerCapture(e.pointerId);
      drag = { mode: e.target.classList.contains("crop-h") ? "size" : "move", sx: e.clientX, sy: e.clientY, c: { x: c.x, y: c.y, w: c.w, h: c.h } };
    });
    fr.addEventListener("pointermove", function (e) {
      if (!drag) return;
      var dx = (e.clientX - drag.sx) / W(), dy = (e.clientY - drag.sy) / H(), o = drag.c;
      var asp = img.naturalWidth / img.naturalHeight; // доля ширины ↔ доля высоты при 4:5
      if (drag.mode === "move") {
        c.x = Math.min(Math.max(0, o.x + dx), 1 - o.w);
        c.y = Math.min(Math.max(0, o.y + dy), 1 - o.h);
      } else {
        var w = Math.max(0.08, o.w + Math.max(dx, dy * RATIO / asp));
        w = Math.min(w, 1 - o.x, (1 - o.y) * RATIO / asp);
        c.w = w; c.h = w * asp / RATIO;
      }
      draw();
    });
    ["pointerup", "pointercancel"].forEach(function (ev) { fr.addEventListener(ev, function () { drag = null; }); });
    window.addEventListener("resize", function () { if (c) draw(); });
    function close() { ov.remove(); document.removeEventListener("keydown", key); }
    function key(e) { if (e.key === "Escape") close(); }
    document.addEventListener("keydown", key);
    ov.addEventListener("click", function (e) {
      var a = e.target.getAttribute && e.target.getAttribute("data-a");
      if (e.target === ov || a === "no") close();
      else if (a === "full") { close(); done(null); }
      else if (a === "ok") { close(); done(c); }
    });
  }
  function cropStr(c) { return c ? [c.x, c.y, c.w, c.h].map(function (v) { return v.toFixed(4); }).join(",") : ""; }

  // уже загруженные фото: ✂ → выбрать область → сохранить
  document.querySelectorAll("[data-crop-btn]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var f = btn.form, inp = f.querySelector("[data-crop-src]");
      cropper(inp.getAttribute("data-crop-src"), null, function (c) {
        if (!c) return;
        inp.value = cropStr(c);
        document.body.classList.add("busy");
        f.submit();
      });
    });
  });

  // ---------- зона загрузки: drag&drop + превью + область ----------
  document.querySelectorAll(".drop").forEach(function (drop) {
    var inp = drop.querySelector("input[type=file]");
    var box = drop.parentNode;
    var prev = box.querySelector(".drop-prev");
    var title = drop.querySelector(".drop-title");
    var formId = inp.getAttribute("form");
    var OK = /^image\/(jpeg|png|webp)$/;
    var crops = [];
    function sync() {
      box.querySelectorAll("input[name=crop]").forEach(function (x) { x.remove(); });
      Array.prototype.forEach.call(inp.files, function (f, i) {
        var h = document.createElement("input");
        h.type = "hidden"; h.name = "crop"; h.value = cropStr(crops[i]);
        if (formId) h.setAttribute("form", formId);
        box.appendChild(h);
      });
    }
    function thumb(fig, url, c) {
      var im = new Image();
      im.onload = function () {
        var k = c || defCrop(im.naturalWidth, im.naturalHeight);
        var cv = document.createElement("canvas"); cv.width = 160; cv.height = 200;
        cv.getContext("2d").drawImage(im, k.x * im.naturalWidth, k.y * im.naturalHeight, k.w * im.naturalWidth, k.h * im.naturalHeight, 0, 0, 160, 200);
        var old = fig.querySelector("canvas"); if (old) old.remove();
        fig.insertBefore(cv, fig.firstChild);
      };
      im.src = url;
    }
    function render(reset) {
      if (reset) crops = [];
      if (!prev) return;
      prev.innerHTML = "";
      Array.prototype.forEach.call(inp.files, function (f, i) {
        var fig = document.createElement("figure");
        if (OK.test(f.type)) {
          var url = URL.createObjectURL(f);
          if (!crops[i]) { // по умолчанию — центр 4:5, чтобы на сайте было как в превью
            var probe = new Image();
            probe.onload = function () { if (!crops[i]) { crops[i] = defCrop(probe.naturalWidth, probe.naturalHeight); sync(); } };
            probe.src = url;
          }
          thumb(fig, url, crops[i]);
          fig.className = "can-crop"; fig.title = "Выбрать область";
          fig.tabIndex = 0;
          fig.addEventListener("click", function () {
            cropper(url, crops[i], function (c) {
              crops[i] = c; sync(); thumb(fig, url, c);
            });
          });
        } else { fig.className = "bad"; fig.textContent = "?"; }
        var cap = document.createElement("figcaption");
        cap.textContent = "✂ " + (f.size >= 1048576 ? (f.size / 1048576).toFixed(1) + " МБ" : Math.max(1, Math.round(f.size / 1024)) + " КБ");
        fig.appendChild(cap);
        prev.appendChild(fig);
      });
      sync();
      var n = inp.files.length;
      title.textContent = n ? "Выбрано файлов: " + n : "Перетащите фото сюда или нажмите";
      drop.classList.toggle("has", n > 0);
    }
    inp.addEventListener("change", function () { render(true); });
    ["dragenter", "dragover"].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("over"); });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove("over"); });
    });
    drop.addEventListener("drop", function (e) {
      var dt = new DataTransfer();
      Array.prototype.forEach.call(e.dataTransfer.files, function (f) { if (OK.test(f.type)) dt.items.add(f); });
      inp.files = dt.files;
      render(true);
    });
  });

  // ---------- таймер блокировки ----------
  var t = document.querySelector("[data-countdown]");
  if (t) {
    var left = parseInt(t.getAttribute("data-countdown"), 10) || 0;
    var mm = t.querySelector("[data-mm]"), ss = t.querySelector("[data-ss]");
    var tick = setInterval(function () {
      left = Math.max(0, left - 1);
      mm.textContent = String(Math.floor(left / 60)).padStart(2, "0");
      ss.textContent = String(left % 60).padStart(2, "0");
      if (!left) { clearInterval(tick); t.classList.add("done"); t.querySelector(".mono").textContent = "Можно пробовать снова"; }
    }, 1000);
  }

  // ---------- показать/скрыть пароль ----------
  var EYE = '<svg class="i-on" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>' +
    '<svg class="i-off" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.6 5.1A10.4 10.4 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.2 4.1M6.6 6.6A17.4 17.4 0 0 0 2 12s3.6 7 10 7a9.7 9.7 0 0 0 5.4-1.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/><path d="M3 3l18 18"/></svg>';
  document.querySelectorAll('input[type="password"]').forEach(function (inp) {
    var wrap = document.createElement("span");
    wrap.className = "pw-wrap";
    inp.parentNode.insertBefore(wrap, inp);
    wrap.appendChild(inp);
    var b = document.createElement("button");
    b.type = "button";
    b.className = "pw-eye";
    b.setAttribute("aria-pressed", "false");
    b.setAttribute("aria-label", "Показать пароль");
    b.innerHTML = EYE; // статичная разметка, без пользовательских данных
    wrap.appendChild(b);
    b.addEventListener("mousedown", function (e) { e.preventDefault(); }); // не уводить фокус из поля
    b.addEventListener("click", function () {
      var show = inp.type === "password";
      inp.type = show ? "text" : "password";
      b.setAttribute("aria-pressed", String(show));
      b.setAttribute("aria-label", show ? "Скрыть пароль" : "Показать пароль");
    });
    if (inp.form) inp.form.addEventListener("submit", function () { inp.type = "password"; }); // менеджеры паролей видят поле пароля
  });

  // ---------- сообщения: закрываются крестиком ----------
  document.querySelectorAll(".flash").forEach(function (f) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "flash-x"; b.setAttribute("aria-label", "Закрыть"); b.textContent = "×";
    b.addEventListener("click", function () { f.classList.add("gone"); setTimeout(function () { f.remove(); }, 200); });
    f.appendChild(b);
  });
})();

// Диалоги настроек: [data-open="id"] открывает <dialog>, [data-close-dlg] / клик по фону закрывают
document.addEventListener("click", function (e) {
  var o = e.target.closest("[data-open]");
  if (o) { var d = document.getElementById(o.dataset.open); if (d && d.showModal) { d.showModal(); var f = d.querySelector("input,textarea"); if (f) f.focus(); } return; }
  var c = e.target.closest("[data-close-dlg]");
  if (c) { c.closest("dialog").close(); return; }
  if (e.target.tagName === "DIALOG") e.target.close();
});
