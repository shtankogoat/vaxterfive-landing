// Заявка → POST /api/lead (сервер сохраняет и отправляет в AmoCRM). Своя валидация — без браузерных подсказок.
(() => {
  const form = document.getElementById('form');
  if (!form) return;
  const okBox = document.getElementById('ok');
  const btn = form.querySelector('[type=submit]');
  const file = document.getElementById('file');
  const fileName = document.getElementById('file-name');
  const drop = form.querySelector('.file');
  const DEF_FILE = fileName ? fileName.textContent : '';
  const MAX = 10 * 1024 * 1024;
  const $ = n => form.elements[n];

  const CHAN = {
    'Telegram': ['Telegram', c => 'https://t.me/vaxterfivebot?start=lead_' + c],
    'MAX': ['MAX', c => 'https://max.ru/id331201426687_bot?start=lead_' + c],
    'ВКонтакте': ['ВКонтакте', c => 'https://vk.me/vaxterfive?ref=lead_' + c]
  };
  // Канал по контакту: ссылка VK → ВКонтакте, ссылка MAX → MAX, остальное (@ник, t.me, телефон) → Telegram
  // Контакт → канал: телефон / @ник / t.me → Telegram, ссылка VK → ВКонтакте, ссылка max.ru → MAX (сервер проверяет так же)
  const parseContact = v => {
    v = String(v || '').trim(); const d = v.replace(/\D/g, '');
    if (/^\+?[\d\s()\-]{10,20}$/.test(v) && d.length >= 10 && d.length <= 15) return 'Telegram';
    if (/^@[A-Za-z0-9_]{4,32}$/.test(v)) return 'Telegram';
    if (/^(?:https?:\/\/)?(?:www\.)?(?:t|telegram)\.me\/[A-Za-z0-9_]{4,32}\/?$/i.test(v)) return 'Telegram';
    if (/^(?:https?:\/\/)?(?:m\.|www\.)?vk\.(?:com|ru|me)\/[A-Za-z0-9_.]{2,64}\/?(?:\?.*)?$/i.test(v)) return 'ВКонтакте';
    if (/^(?:https?:\/\/)?(?:www\.)?max\.ru\/[A-Za-z0-9_\-\/]{2,90}(?:\?.*)?$/i.test(v)) return 'MAX';
    return '';
  };
  const viaOf = c => parseContact(c) || 'Telegram';
  // Готовый текст заявки — клиент вставляет его в чат с ботом
  const DESIGN = { 'Да': 'готов', 'Нет': 'нужна разработка', 'Есть пример': 'есть пример' };
  const MAT = { 'Знаю': 'знаю, какие нужны', 'Помощь': 'нужна помощь с выбором' };
  const buildMsg = v => [
    'Здравствуйте!' + (v.name ? ' Меня зовут ' + v.name + '.' : ''),
    'Хочу заказать: ' + v.what,
    v.qty && 'Количество: ' + v.qty + ' шт.',
    v.date && 'Нужно к: ' + v.date,
    v.design && 'Дизайн: ' + (DESIGN[v.design] || v.design),
    v.mat && 'Материалы: ' + (MAT[v.mat] || v.mat),
    v.kit && 'Макет из конструктора: ' + v.kit
  ].filter(Boolean).join('\n');
  // Копирование СИНХРОННО внутри клика (иначе браузер блокирует буфер обмена)
  const copy = txt => {
    let ok = false;
    const ta = document.createElement('textarea'); ta.value = txt; ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;font-size:16px';
    document.body.appendChild(ta); ta.focus(); ta.select(); ta.setSelectionRange(0, txt.length);
    try { ok = document.execCommand('copy'); } catch (e) {}
    ta.remove();
    try { if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(txt).catch(() => {}); ok = true; } } catch (e) {}
    return ok;
  };
    const ICO = {'Telegram': '<path d="M21.9 4.3 18.7 19.4c-.2 1.1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6.3 13 1.5 11.5c-1-.3-1.1-1 .2-1.5L20.6 2.8c.9-.3 1.6.2 1.3 1.5z"/>','MAX': '<path fill-rule="evenodd" d="M12 2.5a9 9 0 1 1-4.3 16.9L3.4 21l1.3-4A9 9 0 0 1 12 2.5zm0 4.8a4.4 4.4 0 1 0 0 8.8 4.4 4.4 0 0 0 0-8.8z"/>','ВКонтакте': '<path d="M12.8 17.5C6.7 17.5 3.2 13.3 3 6.4h3.1c.1 5 2.3 7.2 4.1 7.6V6.4h2.9v4.4c1.8-.2 3.6-2.2 4.3-4.4h2.9c-.5 2.7-2.5 4.7-3.9 5.5 1.4.7 3.7 2.4 4.5 5.6h-3.2c-.7-2.1-2.4-3.8-4.6-4v4h-.3z"/>'};
  const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  // Успех — окно с текстом заявки (уже в буфере) и кнопками мессенджеров
  const done = (ch, code, msg, copied) => {
    okBox.style.display = 'none';
    const o = document.createElement('div'); o.className = 'vx-done'; o.setAttribute('role', 'dialog'); o.setAttribute('aria-modal', 'true');
    o.innerHTML = '<div class="vx-done-card"><button class="vx-done-x" aria-label="Закрыть">×</button>' +
      '<div class="vx-done-ic"><svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></div>' +
      '<h3>Заявка принята!</h3>' +
      '<p class="vx-done-st">Текст заявки скопирован. Откройте мессенджер, вставьте и отправьте его — менеджер ответит там же.</p>' +
      '<div class="vx-done-msg"><div class="vx-done-mh"><span>Ваше сообщение</span><button type="button" class="vx-done-copy" aria-label="Скопировать"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2.5"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/></svg><i>Скопировать</i></button></div><pre>' + esc(msg) + '</pre></div>' +
      '<div class="vx-done-lbl">Отправить в</div>' +
      '<div class="vx-done-btns">' + [ch].concat(Object.values(CHAN).filter(x => !ch || x[0] !== ch[0])).filter(Boolean).map(x =>
        '<a class="vx-done-go" target="_blank" rel="noopener" href="' + x[1](code) + '"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">' + (ICO[x[0]] || '') + '</svg><span>' + x[0] + '</span></a>').join('') + '</div>' +
      '</div>';
    const st = o.querySelector('.vx-done-st'), cb = o.querySelector('.vx-done-copy');
    const doCopy = () => { const ok = copy(msg); const lb = cb.querySelector('i'); lb.textContent = ok ? 'Скопировано ✓' : 'Выделите текст'; cb.classList.toggle('ok', ok); setTimeout(() => { lb.textContent = 'Скопировать'; cb.classList.remove('ok'); }, 2000); };
    cb.addEventListener('click', doCopy);
    o.querySelectorAll('.vx-done-go').forEach(a => a.addEventListener('click', () => { copy(msg); }));
    const close = () => { o.remove(); document.documentElement.style.overflow = ''; document.removeEventListener('keydown', escKey); };
    const escKey = e => { if (e.key === 'Escape') close(); };
    o.addEventListener('click', e => { if (e.target === o || e.target.closest('.vx-done-x')) close(); });
    document.addEventListener('keydown', escKey);
    document.body.appendChild(o); document.documentElement.style.overflow = 'hidden';
    if (!copied) st.textContent = 'Скопируйте текст заявки кнопкой ниже, откройте мессенджер, вставьте и отправьте его — менеджер ответит там же.';
    o.querySelector('.vx-done-go').focus();
  };
  const show = (text, bad) => { okBox.className = 'ok'; okBox.textContent = text; okBox.classList.toggle('bad', !!bad); okBox.style.display = 'block'; };
  const setFile = f => { if (!fileName) return; fileName.textContent = f ? f.name : DEF_FILE; drop.classList.toggle('has', !!f); };

  // ---- ошибки у полей
  const holder = el => el.closest('.f') || el.closest('.consent');
  const setErr = (el, msg) => {
    const h = holder(el); if (!h) return;
    let e = h.querySelector('.f-err');
    if (msg) {
      if (!e) { e = document.createElement('div'); e.className = 'f-err'; e.setAttribute('role', 'alert'); (h.classList.contains('consent') ? h.parentNode : h).appendChild(e); if (h.classList.contains('consent')) e.classList.add('consent-err'); }
      e.textContent = msg; h.classList.add('invalid'); el.setAttribute('aria-invalid', 'true');
    } else {
      if (e) e.remove();
      const ce = h.classList.contains('consent') && h.parentNode.querySelector('.consent-err'); if (ce) ce.remove();
      h.classList.remove('invalid'); el.removeAttribute('aria-invalid');
    }
  };

  // ---- маски
  $('qty').addEventListener('input', e => { e.target.value = e.target.value.replace(/\D/g, '').replace(/^0+/, ''); });
  $('date_ru').addEventListener('input', e => {
    const d = e.target.value.replace(/\D/g, '').slice(0, 8);
    e.target.value = d.length > 4 ? d.slice(0, 2) + '.' + d.slice(2, 4) + '.' + d.slice(4) : d.length > 2 ? d.slice(0, 2) + '.' + d.slice(2) : d;
  });

  const parseDate = v => {
    const m = v.match(/^(\d{2})\.(\d{2})\.(\d{4})$/); if (!m) return null;
    const d = new Date(+m[3], +m[2] - 1, +m[1]);
    if (d.getFullYear() !== +m[3] || d.getMonth() !== +m[2] - 1 || d.getDate() !== +m[1]) return null;
    return d;
  };

  const rules = {
    what: v => v.trim() ? '' : 'Опишите, что нужно произвести',
    qty: v => !v ? 'Укажите количество' : +v < 1 ? 'Минимум 1 изделие' : '',
    date_ru: v => {
      if (!v) return '';
      const d = parseDate(v); if (!d) return 'Дата в формате дд.мм.гггг';
      const today = new Date(); today.setHours(0, 0, 0, 0);
      return d < today ? 'Дата уже прошла' : '';
    },
    name: v => v.trim() ? '' : 'Как к вам обращаться?',
  };
  const check = n => { const el = $(n); const msg = rules[n](el.value); setErr(el, msg); return !msg; };
  Object.keys(rules).forEach(n => {
    $(n).addEventListener('blur', () => { if ($(n).value) check(n); });
    $(n).addEventListener('input', () => { if (holder($(n)).classList.contains('invalid')) check(n); });
  });
  const consent = $('consent');
  consent.addEventListener('change', () => { if (consent.checked) setErr(consent, ''); });

  if (file) {
    file.addEventListener('change', () => setFile(file.files[0]));
    ['dragenter', 'dragover'].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.remove('over'); }));
    drop.addEventListener('drop', e => {
      const f = e.dataTransfer.files[0]; if (!f) return;
      const dt = new DataTransfer(); dt.items.add(f); file.files = dt.files; setFile(f);
    });
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();
    okBox.style.display = 'none';
    const bad = Object.keys(rules).filter(n => !check(n));
    if (!consent.checked) { setErr(consent, 'Нужно согласие на обработку данных'); bad.push('consent'); }
    if (bad.length) { const first = $(bad[0]); first.focus({ preventScroll: true }); first.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
    const f = file && file.files[0];
    if (f && f.size > MAX) { show('Файл больше 10 МБ — пришлите его менеджеру в мессенджер.', true); return; }

    const data = new FormData(form);
    data.delete('date_ru');
    const d = parseDate($('date_ru').value);
    if (d) data.set('date', `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`);
    const via = 'Telegram';
    data.set('via', via);
    data.set('page', location.origin + location.pathname);
    if (/^#k=/.test(location.hash)) data.set('kit', location.origin + '/' + location.hash);
    const msg = buildMsg({ name: (data.get('name') || '').trim(), what: (data.get('what') || '').trim(), qty: (data.get('qty') || '').trim(),
      date: $('date_ru').value.trim(), design: data.get('design'), mat: data.get('mat'), kit: data.get('kit') });
    const copied = copy(msg);
    btn.disabled = true; const label = btn.textContent; btn.textContent = 'ОТПРАВЛЯЕМ…';
    try {
      const r = await fetch('/api/lead', { method: 'POST', body: data, credentials: 'same-origin' });
      const res = await r.json().catch(() => ({}));
      if (!r.ok || !res.ok) throw new Error(res.error || '');
      const code = res.code || '';
      done(CHAN[via], code, msg, copied);
      form.reset(); setFile(null);
    } catch (err) {
      show((err && err.message) || 'Не удалось отправить заявку. Позвоните нам: +7 (900) 474-30-00 или напишите в мессенджер.', true);
    }
    btn.disabled = false; btn.textContent = label;
  });
})();
