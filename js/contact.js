// Окно «Связаться»: все кнопки с href="#contact" открывают выбор мессенджера.
(() => {
  const L = [
    ['tg', 'Telegram', '@vaxterfivebot', 'https://t.me/vaxterfivebot',
      '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M21.9 4.3 18.7 19.4c-.2 1.1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6.3 13 1.5 11.5c-1-.3-1.1-1 .2-1.5L20.6 2.8c.9-.3 1.6.2 1.3 1.5z"/></svg>'],
    ['max', 'MAX', 'Чат-бот Vaxter Five', 'https://max.ru/id331201426687_bot', '<img src="/img/icons/max.png" alt="" width="28" height="28">'],
    ['vk', 'ВКонтакте', 'vk.com/vaxterfive', 'https://vk.com/vaxterfive',
      '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12.8 17.5C6.7 17.5 3.2 13.3 3 6.4h3.1c.1 5 2.3 7.2 4.1 7.6V6.4h2.9v4.4c1.8-.2 3.6-2.2 4.3-4.4h2.9c-.5 2.7-2.5 4.7-3.9 5.5 1.4.7 3.7 2.4 4.5 5.6h-3.2c-.7-2.1-2.4-3.8-4.6-4v4h-.3z"/></svg>'],
  ];
  const css = `
.cm{position:fixed;inset:0;z-index:300;display:none;align-items:center;justify-content:center;padding:16px;background:rgba(11,13,18,.55);backdrop-filter:blur(6px)}
.cm.open{display:flex}
.cm-box{position:relative;width:100%;max-width:440px;background:#fff;border-radius:22px;padding:30px 26px 24px;box-shadow:0 30px 80px -20px rgba(0,0,0,.45);animation:cmIn .25s ease}
@keyframes cmIn{from{opacity:0;transform:translateY(14px) scale(.98)}}
.cm-x{position:absolute;top:14px;right:14px;width:36px;height:36px;border-radius:50%;border:0;background:#f5f6f8;font-size:20px;line-height:1;cursor:pointer;color:#0b0d12}
.cm h3{font-size:26px;font-weight:900;letter-spacing:-.03em;line-height:1.05;margin:0 40px 8px 0;color:#0b0d12}
.cm p{color:#4a505c;font-size:15px;line-height:1.5;margin:0 0 20px}
.cm-l{display:grid;gap:10px}
.cm-a{display:flex;align-items:center;gap:14px;padding:14px 16px;border:1px solid #e6e8ec;border-radius:16px;color:#0b0d12;text-decoration:none;transition:transform .2s,box-shadow .2s,border-color .2s}
.cm-a:hover{transform:translateY(-2px);border-color:transparent;box-shadow:0 14px 30px -18px rgba(11,13,18,.4)}
.cm-i{width:46px;height:46px;flex:none;border-radius:13px;display:grid;place-items:center;color:#fff}
.cm-i img{width:28px;height:28px;object-fit:contain}
.cm-a.tg .cm-i{background:#229ED9}.cm-a.vk .cm-i{background:#0077FF}.cm-a.max .cm-i{background:linear-gradient(135deg,#3d5afe,#9b4dff)}
.cm-t{flex:1;display:flex;flex-direction:column;min-width:0}
.cm-t b{font-size:17px;font-weight:800}.cm-t small{color:#8a909c;font-size:13px}
.cm-a .cm-arr{color:#8a909c;font-size:20px}
.cm-note{display:none;align-items:center;gap:10px;margin:-6px 0 18px;padding:12px 14px;border-radius:14px;background:#eaf7ee;color:#11633a;font-size:14px;font-weight:600;line-height:1.35}
.cm-note.on{display:flex}
.cm-note svg{flex:none}
.cm-ph{display:block;text-align:center;margin-top:16px;color:#4a505c;font-size:14px;text-decoration:none}
.cm-ph b{color:#0b0d12}`;
  const st = document.createElement('style'); st.textContent = css; document.head.append(st);
  const m = document.createElement('div');
  m.className = 'cm'; m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true'); m.setAttribute('aria-label', 'Связаться с менеджером');
  m.innerHTML = `<div class="cm-box">
  <button class="cm-x" type="button" aria-label="Закрыть">×</button>
  <h3>Рассчитаем ваш заказ</h3>
  <p>Напишите в удобный мессенджер — менеджер примет всю информацию и сразу сориентирует по срокам и стоимости изделий.</p>
  <div class="cm-note" id="cm-note"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12l5 5L20 7"/></svg><span></span></div>
  <div class="cm-l">${L.map(([k, n, s, u, i]) => `<a class="cm-a ${k}" href="${u}" target="_blank" rel="noopener"><span class="cm-i">${i}</span><span class="cm-t"><b>${n}</b><small>${s}</small></span><span class="cm-arr">→</span></a>`).join('')}</div>
  <a class="cm-ph" href="tel:+79004743000">или позвоните: <b>+7 (900) 474-30-00</b></a>
</div>`;
  document.body.append(m);
  let last = null;
  const open = (note) => { const n = m.querySelector('#cm-note'); n.classList.toggle('on', !!note); n.querySelector('span').textContent = note || ''; last = document.activeElement; m.classList.add('open'); document.body.style.overflow = 'hidden'; m.querySelector('.cm-a').focus(); };
  const close = () => { m.classList.remove('open'); document.body.style.overflow = ''; if (last) last.focus(); if (/^#contact$/.test(location.hash)) history.replaceState(null, '', location.pathname + location.search); };
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href$="#contact"]');
    if (a) { e.preventDefault(); open(a.dataset.note); }
  });
  m.addEventListener('click', e => { if (e.target === m || e.target.closest('.cm-x')) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && m.classList.contains('open')) close(); });
  if (/^#contact$/.test(location.hash)) open();
})();
