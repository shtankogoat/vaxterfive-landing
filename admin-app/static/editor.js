// Редактор статей: contenteditable + свой тулбар. Без CDN, без inline-скриптов (CSP script-src 'self').
// Итоговый HTML всё равно чистится на сервере (articles_admin.sanitize) — здесь только удобство.
(function () {
  "use strict";
  var src = document.getElementById("art-body");
  var cfg = document.getElementById("art-cfg");
  if (!src || !cfg) return;
  var form = src.form;

  // ---------- разметка ----------
  var wrap = document.createElement("div");
  wrap.className = "ed";
  var BTN = [
    ["p", "Абзац", "Обычный текст"], ["h2", "H2", "Заголовок раздела"], ["h3", "H3", "Подзаголовок"], ["|"],
    ["bold", "<b>Ж</b>", "Жирный (Ctrl+B)"], ["italic", "<i>К</i>", "Курсив (Ctrl+I)"], ["|"],
    ["ul", "• Список", "Маркированный список"], ["ol", "1. Список", "Нумерованный список"],
    ["quote", "« Цитата »", "Цитата"], ["link", "Ссылка", "Ссылка (Ctrl+K)"], ["|"],
    ["image", "+ Фото", "Вставить фото с подписью"], ["|"], ["undo", "↶", "Отменить"], ["redo", "↷", "Повторить"]
  ];
  var bar = document.createElement("div");
  bar.className = "ed-bar";
  bar.setAttribute("role", "toolbar");
  BTN.forEach(function (b) {
    if (b[0] === "|") { var s = document.createElement("span"); s.className = "ed-sep"; bar.appendChild(s); return; }
    var x = document.createElement("button");
    x.type = "button"; x.className = "ed-b"; x.dataset.cmd = b[0]; x.title = b[2]; x.setAttribute("aria-label", b[2]);
    x.innerHTML = b[1]; // статичные подписи
    bar.appendChild(x);
  });
  var linkRow = document.createElement("div");
  linkRow.className = "ed-link"; linkRow.hidden = true;
  linkRow.innerHTML = '<input type="text" inputmode="url" placeholder="https://… или /catalog/…" aria-label="Адрес ссылки">' +
    '<button type="button" class="ed-lb pri" data-l="ok">Применить</button>' +
    '<button type="button" class="ed-lb" data-l="rm">Убрать ссылку</button>' +
    '<button type="button" class="ed-lb" data-l="x">Отмена</button>';
  var ed = document.createElement("div");
  ed.className = "ed-area"; ed.contentEditable = "true"; ed.setAttribute("role", "textbox");
  ed.setAttribute("aria-multiline", "true"); ed.setAttribute("aria-label", "Текст статьи");
  ed.dataset.ph = "Начните писать статью… Заголовки, списки и фото — на панели сверху.";
  var status = document.createElement("div");
  status.className = "ed-status mono"; status.setAttribute("aria-live", "polite");
  var file = document.createElement("input");
  file.type = "file"; file.accept = "image/jpeg,image/png,image/webp"; file.hidden = true;
  wrap.appendChild(bar); wrap.appendChild(linkRow); wrap.appendChild(ed); wrap.appendChild(status); wrap.appendChild(file);
  src.hidden = true;
  src.parentNode.insertBefore(wrap, src.nextSibling);

  // ---------- очистка (зеркало серверного allowlist) ----------
  var ALLOW = { P: 1, H2: 1, H3: 1, STRONG: 1, EM: 1, UL: 1, OL: 1, LI: 1, A: 1, BLOCKQUOTE: 1, FIGURE: 1, IMG: 1, FIGCAPTION: 1, BR: 1 };
  var REN = { B: "STRONG", I: "EM", DIV: "P", H1: "H2", H4: "H3", H5: "H3", H6: "H3" };
  var DROP = { SCRIPT: 1, STYLE: 1, IFRAME: 1, OBJECT: 1, EMBED: 1, TEMPLATE: 1, NOSCRIPT: 1, SVG: 1, META: 1, LINK: 1, TITLE: 1 };
  var IMG_OK = /^\/img\/articles\/a-[0-9a-f]{16}\.webp$/;
  function cleanNode(node) {
    Array.prototype.slice.call(node.childNodes).forEach(function (n) {
      if (n.nodeType === 3) return;
      if (n.nodeType !== 1) { n.remove(); return; }
      var tag = REN[n.tagName] || n.tagName;
      if (DROP[tag]) { n.remove(); return; }
      cleanNode(n);
      if (!ALLOW[tag] || (tag === "IMG" && !IMG_OK.test(n.getAttribute("src") || ""))) {
        while (n.firstChild) n.parentNode.insertBefore(n.firstChild, n);
        n.remove(); return;
      }
      var el = n;
      if (tag !== n.tagName) { el = document.createElement(tag); while (n.firstChild) el.appendChild(n.firstChild); n.replaceWith(el); }
      Array.prototype.slice.call(el.attributes).forEach(function (a) {
        var keep = (tag === "A" && a.name === "href") || (tag === "IMG" && (a.name === "src" || a.name === "alt"));
        if (!keep) el.removeAttribute(a.name);
      });
      if (tag === "FIGURE") { el.contentEditable = "false"; var c = el.querySelector("figcaption"); if (!c) { c = document.createElement("figcaption"); el.appendChild(c); } c.contentEditable = "true"; c.dataset.ph = "Подпись к фото"; }
    });
  }
  function load(html) {
    var t = document.createElement("template");
    t.innerHTML = html || "";
    cleanNode(t.content);
    ed.innerHTML = "";
    ed.appendChild(t.content);
    if (!ed.firstChild) ed.innerHTML = "<p><br></p>";
  }
  function serialize() {
    var c = ed.cloneNode(true);
    c.querySelectorAll("[contenteditable],[data-ph]").forEach(function (x) { x.removeAttribute("contenteditable"); x.removeAttribute("data-ph"); });
    c.querySelectorAll("figure.sel").forEach(function (x) { x.classList.remove("sel"); x.removeAttribute("class"); });
    return c.innerHTML;
  }
  load(src.value);
  try { document.execCommand("defaultParagraphSeparator", false, "p"); document.execCommand("styleWithCSS", false, false); } catch (e) {}

  // ---------- выделение ----------
  var saved = null;
  function inEd(r) { return r && ed.contains(r.commonAncestorContainer); }
  function save() { var s = getSelection(); if (s.rangeCount && inEd(s.getRangeAt(0))) saved = s.getRangeAt(0).cloneRange(); }
  function restore() { ed.focus(); if (saved) { var s = getSelection(); s.removeAllRanges(); s.addRange(saved); } }
  document.addEventListener("selectionchange", function () { save(); state(); });
  function blockOf(n) {
    while (n && n !== ed) { if (n.nodeType === 1 && /^(P|H2|H3|LI|BLOCKQUOTE|FIGURE)$/.test(n.tagName)) return n; n = n.parentNode; }
    return null;
  }
  function state() {
    var s = getSelection(); if (!s.rangeCount || !inEd(s.getRangeAt(0))) return;
    var b = blockOf(s.anchorNode), q = b && b.closest ? b.closest("blockquote") : null, li = b && b.closest ? b.closest("ul,ol") : null;
    bar.querySelectorAll(".ed-b").forEach(function (x) {
      var c = x.dataset.cmd, on = false;
      try {
        if (c === "bold" || c === "italic") on = document.queryCommandState(c);
        else if (c === "h2" || c === "h3") on = !!(b && b.tagName === c.toUpperCase());
        else if (c === "quote") on = !!q;
        else if (c === "ul" || c === "ol") on = !!(li && li.tagName === c.toUpperCase());
        else if (c === "link") on = !!(s.anchorNode && s.anchorNode.parentElement && s.anchorNode.parentElement.closest("a"));
      } catch (e) {}
      x.classList.toggle("on", on);
    });
  }

  // ---------- команды ----------
  function fmt(tag) { restore(); document.execCommand("formatBlock", false, "<" + tag + ">"); }
  function cmd(c) {
    if (c === "image") { save(); file.click(); return; }
    if (c === "link") { openLink(); return; }
    restore();
    if (inCaption() && c !== "undo" && c !== "redo") { status.textContent = "В подписи к фото форматирование не нужно — поставьте курсор в текст статьи."; return; }
    var b = blockOf(getSelection().anchorNode);
    switch (c) {
      case "p": fmt("p"); break;
      case "h2": case "h3": fmt(b && b.tagName === c.toUpperCase() ? "p" : c); break;
      case "bold": case "italic": case "undo": case "redo": document.execCommand(c); break;
      case "ul": document.execCommand("insertUnorderedList"); break;
      case "ol": document.execCommand("insertOrderedList"); break;
      case "quote": fmt(b && b.closest && b.closest("blockquote") ? "p" : "blockquote"); break;
    }
    tidy(); state();
  }
  bar.addEventListener("mousedown", function (e) { if (e.target.closest(".ed-b")) e.preventDefault(); });
  bar.addEventListener("click", function (e) { var b = e.target.closest(".ed-b"); if (b) cmd(b.dataset.cmd); });
  ed.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "л")) { e.preventDefault(); openLink(); }
    var sel = ed.querySelector("figure.sel");
    if (sel && (e.key === "Backspace" || e.key === "Delete")) { e.preventDefault(); var p = document.createElement("p"); p.innerHTML = "<br>"; sel.replaceWith(p); caretTo(p); }
  });

  // ---------- ссылки (своя панель вместо window.prompt) ----------
  var linkInp = linkRow.querySelector("input");
  function openLink() {
    save();
    var a = saved && (saved.startContainer.nodeType === 1 ? saved.startContainer : saved.startContainer.parentElement).closest("a");
    linkInp.value = a ? a.getAttribute("href") : "";
    linkRow.hidden = false; linkInp.focus();
  }
  function closeLink() { linkRow.hidden = true; restore(); }
  linkRow.addEventListener("click", function (e) {
    var k = e.target.dataset && e.target.dataset.l; if (!k) return;
    if (k === "x") return closeLink();
    restore();
    if (k === "rm") document.execCommand("unlink");
    else {
      var u = linkInp.value.trim();
      if (u && !/^(https?:\/\/|mailto:|tel:|\/|#)/i.test(u)) u = "https://" + u;
      if (u) {
        if (saved && saved.collapsed) { document.execCommand("insertHTML", false, '<a href="' + u.replace(/"/g, "%22") + '">' + u.replace(/[<>&]/g, "") + "</a>"); }
        else document.execCommand("createLink", false, u);
      }
    }
    linkRow.hidden = true; state();
  });
  linkInp.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); linkRow.querySelector('[data-l="ok"]').click(); }
    if (e.key === "Escape") { e.preventDefault(); closeLink(); }
  });

  // ---------- фото с подписью ----------
  function caretTo(el) { var r = document.createRange(); r.selectNodeContents(el); r.collapse(true); var s = getSelection(); s.removeAllRanges(); s.addRange(r); ed.focus(); }
  function insertFigure(url) {
    restore();
    var fig = document.createElement("figure"); fig.contentEditable = "false";
    var img = document.createElement("img"); img.src = url; img.alt = "";
    var cap = document.createElement("figcaption"); cap.contentEditable = "true"; cap.dataset.ph = "Подпись к фото";
    fig.appendChild(img); fig.appendChild(cap);
    var after = document.createElement("p"); after.innerHTML = "<br>";
    var s = getSelection(), b = s.rangeCount && inEd(s.getRangeAt(0)) ? blockOf(s.anchorNode) : null;
    if (b && b.closest("li")) b = b.closest("ul,ol");
    if (b && b.closest("blockquote")) b = b.closest("blockquote");
    if (b) { b.after(fig); } else ed.appendChild(fig);
    fig.after(after);
    if (b && b.tagName === "P" && !b.textContent.trim()) b.remove();
    cap.focus();
  }
  function upload(f) {
    var fd = new FormData();
    fd.append("csrf", cfg.dataset.csrf); fd.append("image", f);
    status.textContent = "Загружаем фото…"; wrap.classList.add("busy");
    fetch(cfg.dataset.upload, { method: "POST", body: fd, credentials: "same-origin" })
      .then(function (r) { return r.json().catch(function () { return { ok: false, error: "Сессия истекла — обновите страницу." }; }); })
      .then(function (j) {
        wrap.classList.remove("busy");
        if (!j.ok) { status.textContent = "Ошибка: " + (j.error || "не удалось загрузить"); status.classList.add("err"); return; }
        status.textContent = "Фото добавлено — напишите подпись под ним."; status.classList.remove("err");
        insertFigure(j.url);
      })
      .catch(function () { wrap.classList.remove("busy"); status.textContent = "Ошибка сети при загрузке фото."; status.classList.add("err"); });
  }
  file.addEventListener("change", function () { if (file.files[0]) upload(file.files[0]); file.value = ""; });
  ed.addEventListener("click", function (e) {
    ed.querySelectorAll("figure.sel").forEach(function (x) { x.classList.remove("sel"); });
    var f = e.target.tagName === "IMG" && e.target.closest("figure");
    if (f) { f.classList.add("sel"); status.textContent = "Фото выбрано: Delete — удалить."; }
  });
  ed.addEventListener("dragover", function (e) { if (e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types, "Files") >= 0) e.preventDefault(); });
  ed.addEventListener("drop", function (e) {
    var f = e.dataTransfer && e.dataTransfer.files[0];
    if (f && /^image\//.test(f.type)) { e.preventDefault(); upload(f); }
  });

  // ---------- вставка: чистим чужое форматирование ----------
  ed.addEventListener("paste", function (e) {
    var cd = e.clipboardData; if (!cd) return;
    var f = cd.files && cd.files[0];
    if (f && /^image\//.test(f.type)) { e.preventDefault(); save(); upload(f); return; }
    var h = cd.getData("text/html");
    e.preventDefault();
    if (inCaption()) { document.execCommand("insertText", false, (cd.getData("text/plain") || "").replace(/\s+/g, " ")); return; }
    if (h) {
      var t = document.createElement("template"); t.innerHTML = h; cleanNode(t.content);
      var d = document.createElement("div"); d.appendChild(t.content);
      document.execCommand("insertHTML", false, d.innerHTML);
    } else {
      var txt = cd.getData("text/plain") || "";
      var html = txt.split(/\n{2,}/).map(function (p) { return "<p>" + p.replace(/[&<>]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]; }).replace(/\n/g, "<br>") + "</p>"; }).join("");
      document.execCommand("insertHTML", false, html);
    }
    tidy();
  });

  // браузер иногда оставляет <span style>, <font>, <p><ul>…</ul></p>, голый текст — приводим к допустимой структуре
  var BLK = /^(P|H2|H3|UL|OL|BLOCKQUOTE|FIGURE|DIV)$/;
  function tidy() {
    ed.querySelectorAll("span,font").forEach(function (s) { while (s.firstChild) s.parentNode.insertBefore(s.firstChild, s); s.remove(); });
    ed.querySelectorAll("p,h2,h3").forEach(function (b) { // блок внутри абзаца/заголовка → разворачиваем обёртку
      if (!b.isConnected) return;
      var hasBlock = Array.prototype.some.call(b.children, function (c) { return BLK.test(c.tagName); });
      if (hasBlock) { while (b.firstChild) b.parentNode.insertBefore(b.firstChild, b); b.remove(); }
    });
    ed.querySelectorAll("figcaption *").forEach(function (x) { if (x.isConnected) x.replaceWith(document.createTextNode(x.textContent)); });
    var run = null; // подряд идущие «строчные» узлы верхнего уровня → один абзац
    Array.prototype.slice.call(ed.childNodes).forEach(function (n) {
      var inline = (n.nodeType === 3 && (n.textContent.trim() || run)) || (n.nodeType === 1 && !BLK.test(n.tagName));
      if (inline) { if (!run) { run = document.createElement("p"); n.before(run); } run.appendChild(n); }
      else run = null;
    });
    ed.querySelectorAll("div").forEach(function (d) { var p = document.createElement("p"); while (d.firstChild) p.appendChild(d.firstChild); d.replaceWith(p); });
    ed.querySelectorAll("figure").forEach(function (f) { if (!f.nextElementSibling) { var p = document.createElement("p"); p.innerHTML = "<br>"; f.after(p); } });
    ed.querySelectorAll("[style]").forEach(function (x) { x.removeAttribute("style"); });
  }
  // подпись к фото: Enter → к абзацу под фото; форматирование в подписи не применяем
  function inCaption() { var s = getSelection(); var n = s.anchorNode; return n && (n.nodeType === 1 ? n : n.parentElement).closest("figcaption"); }
  ed.addEventListener("keydown", function (e) {
    var cap = inCaption(); if (!cap) return;
    if (e.key === "Enter") { e.preventDefault(); var f = cap.closest("figure"); var nx = f.nextElementSibling; if (!nx || nx.tagName !== "P") { nx = document.createElement("p"); nx.innerHTML = "<br>"; f.after(nx); } caretTo(nx); }
    if ((e.ctrlKey || e.metaKey) && /^[biu]$/i.test(e.key)) e.preventDefault();
  }, true);
  ed.addEventListener("input", function () { tidy(); dirty = true; });

  // ---------- отправка ----------
  var dirty = false;
  form.addEventListener("input", function () { dirty = true; });
  form.addEventListener("submit", function () { src.value = serialize(); dirty = false; });
  window.addEventListener("beforeunload", function (e) { if (dirty) { e.preventDefault(); e.returnValue = ""; } });

  // счётчик символов краткого описания
  document.querySelectorAll("textarea[data-count]").forEach(function (t) {
    var s = document.createElement("small"); s.className = "cnt mono"; t.after(s);
    function u() { s.textContent = t.value.length + " / " + t.maxLength; }
    t.addEventListener("input", u); u();
  });
})();
