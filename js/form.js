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

  const show = (text, bad) => { okBox.textContent = text; okBox.classList.toggle('bad', !!bad); okBox.style.display = 'block'; };
  const setFile = f => { fileName.textContent = f ? f.name : DEF_FILE; drop.classList.toggle('has', !!f); };

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
    contact: v => {
      v = v.trim(); if (!v) return 'Оставьте телефон или @telegram';
      if (/^@[A-Za-z0-9_]{4,32}$/.test(v)) return '';
      const digits = v.replace(/\D/g, '');
      return /^[+\d\s()\-]+$/.test(v) && digits.length >= 10 && digits.length <= 15 ? '' : 'Телефон (+7 900 …) или ник @telegram';
    },
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
    data.set('page', location.origin + location.pathname);
    if (/^#k=/.test(location.hash)) data.set('kit', location.origin + '/' + location.hash);
    btn.disabled = true; const label = btn.textContent; btn.textContent = 'ОТПРАВЛЯЕМ…';
    try {
      const r = await fetch('/api/lead', { method: 'POST', body: data, credentials: 'same-origin' });
      const res = await r.json().catch(() => ({}));
      if (!r.ok || !res.ok) throw new Error(res.error || '');
      show('Спасибо! Заявка отправлена — менеджер свяжется с вами в ближайшее время.');
      form.reset(); setFile(null);
    } catch (err) {
      show((err && err.message) || 'Не удалось отправить заявку. Позвоните нам: +7 (900) 474-30-00 или напишите в мессенджер.', true);
    }
    btn.disabled = false; btn.textContent = label;
  });
})();
