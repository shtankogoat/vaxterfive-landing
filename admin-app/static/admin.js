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

  // ---------- зона загрузки: drag&drop + превью ----------
  document.querySelectorAll(".drop").forEach(function (drop) {
    var inp = drop.querySelector("input[type=file]");
    var prev = drop.parentNode.querySelector(".drop-prev");
    var title = drop.querySelector(".drop-title");
    var OK = /^image\/(jpeg|png|webp)$/;
    function render() {
      if (!prev) return;
      prev.innerHTML = "";
      Array.prototype.forEach.call(inp.files, function (f) {
        var fig = document.createElement("figure");
        if (OK.test(f.type)) {
          var img = document.createElement("img");
          img.alt = "";
          img.src = URL.createObjectURL(f);
          img.onload = function () { URL.revokeObjectURL(img.src); };
          fig.appendChild(img);
        } else { fig.className = "bad"; fig.textContent = "?"; }
        var cap = document.createElement("figcaption");
        cap.textContent = f.size >= 1048576 ? (f.size / 1048576).toFixed(1) + " МБ" : Math.max(1, Math.round(f.size / 1024)) + " КБ";
        fig.appendChild(cap);
        prev.appendChild(fig);
      });
      var n = inp.files.length;
      title.textContent = n ? "Выбрано файлов: " + n : "Перетащите фото сюда или нажмите";
      drop.classList.toggle("has", n > 0);
    }
    inp.addEventListener("change", render);
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
      render();
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
