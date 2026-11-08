/* Vaxter Five — конструктор формы. Vanilla JS, без зависимостей. */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };

  /* ================= справочники ================= */
  var PALETTE = [
    ['Белый', '#ffffff'], ['Чёрный', '#0b0d12'], ['Тёмно-синий', '#14213d'], ['Синий', '#1f4bff'], ['Голубой', '#4cb8f5'],
    ['Бирюзовый', '#00a6a6'], ['Мятный', '#5fe0b7'], ['Зелёный', '#14a44d'], ['Тёмно-зелёный', '#0d4a2f'], ['Лайм', '#c6f432'],
    ['Жёлтый', '#ffd60a'], ['Золото', '#c9a227'], ['Оранжевый', '#ff6b1a'], ['Красный', '#e3241b'], ['Бордовый', '#7a1426'],
    ['Розовый', '#ff4f9a'], ['Фиолетовый', '#6a35d9'], ['Серый', '#8a909c']
  ];
  // t: top | bottom | acc ; vb: viewBox ; dw: «реальная» ширина в единицах сцены
  var TOPVB = [0, -44, 400, 494];
  var ITEMS = {
    tee: { n: 'Футболка', t: 'top', vb: TOPVB, dw: 400 },
    polo: { n: 'Поло', t: 'top', vb: TOPVB, dw: 400 },
    tank: { n: 'Майка', t: 'top', vb: TOPVB, dw: 400 },
    long: { n: 'Лонгслив', t: 'top', vb: TOPVB, dw: 400 },
    sweat: { n: 'Свитшот', t: 'top', vb: TOPVB, dw: 410 },
    hoodie: { n: 'Худи', t: 'top', vb: TOPVB, dw: 410 },
    jacket: { n: 'Ветровка', t: 'top', vb: TOPVB, dw: 420 },
    shorts: { n: 'Шорты', t: 'bottom', vb: [0, 0, 400, 320], dw: 236 },
    pants: { n: 'Брюки', t: 'bottom', vb: [0, 0, 400, 760], dw: 236 },
    socks: { n: 'Гетры', t: 'acc', vb: [0, 0, 300, 450], dw: 150 },
    ball: { n: 'Мяч', t: 'acc', vb: [0, 0, 400, 400], dw: 170 }
  };
  var ORDER = ['tee', 'polo', 'tank', 'long', 'sweat', 'hoodie', 'jacket', 'shorts', 'pants', 'socks', 'ball'];
  var FONTS = [['oswald', 'Oswald', 'Oswald, Inter Tight, sans-serif', 700, 1], ['russo', 'Russo One', 'Russo One, Inter Tight, sans-serif', 400, .86], ['inter', 'Inter Tight', 'Inter Tight, sans-serif', 900, .86]];
  var PATTERNS = [['plain', 'Гладкий'], ['stripes', 'Полосы'], ['hoops', 'Обручи'], ['sash', 'Диагональ'], ['halves', 'Половины'],
    ['grad', 'Градиент'], ['chevron', 'Шеврон'], ['yoke', 'Кокетка'], ['pin', 'Пинстрайп'], ['geo', 'Геометрия']];
  var ZONES = { body: 'Основа', sleeve: 'Рукава', trim: 'Отделка', side: 'Вставки', pat: 'Рисунок', bottom: 'Низ', text: 'Надписи', num: 'Номер', outl: 'Обводка' };
  var ZONE_HELP = { trim: 'воротник, манжеты, пояс', side: 'боковые вставки, лампасы', bottom: 'шорты, брюки, гетры' };
  var LOGOPOS = [['l', 'Левая грудь'], ['c', 'По центру'], ['r', 'Правая грудь']];
  var DEF = {
    m: 'kit', g: 'tee', k: ['tee', 'shorts', 'socks'], p: 'sash', font: 'oswald', team: 'VAXTER', name: 'ИВАНОВ', num: '10',
    fnum: 0, snum: 1, ow: 1, lx: 252, ly: 104, ls: 40,
    c: { body: '#1f4bff', sleeve: '#1f4bff', trim: '#0b0d12', side: '#0b0d12', pat: '#ffffff', bottom: '#0b0d12', text: '#ffffff', num: '#ffffff', outl: '#0b0d12' }
  };
  function P(p, body, sleeve, trim, side, pat, bottom, text, num, outl) { return { p: p, c: { body: body, sleeve: sleeve, trim: trim, side: side, pat: pat, bottom: bottom, text: text, num: num, outl: outl } }; }
  var PRESETS = [
    ['Шторм', P('sash', '#1f4bff', '#1f4bff', '#0b0d12', '#0b0d12', '#ffffff', '#0b0d12', '#ffffff', '#ffffff', '#0b0d12')],
    ['Классика', P('stripes', '#ffffff', '#e3241b', '#e3241b', '#e3241b', '#e3241b', '#ffffff', '#0b0d12', '#0b0d12', '#ffffff')],
    ['Золото', P('pin', '#0b0d12', '#0b0d12', '#c9a227', '#c9a227', '#2a2d36', '#0b0d12', '#c9a227', '#c9a227', '#0b0d12')],
    ['Лес', P('hoops', '#0d4a2f', '#0d4a2f', '#ffffff', '#ffffff', '#14a44d', '#ffffff', '#ffffff', '#ffffff', '#0d4a2f')],
    ['Закат', P('grad', '#ffd60a', '#ff6b1a', '#0b0d12', '#0b0d12', '#e3241b', '#0b0d12', '#0b0d12', '#ffffff', '#0b0d12')],
    ['Бордо', P('chevron', '#7a1426', '#7a1426', '#14213d', '#14213d', '#14213d', '#14213d', '#ffffff', '#ffffff', '#14213d')],
    ['Лёд', P('geo', '#4cb8f5', '#ffffff', '#14213d', '#ffffff', '#14213d', '#14213d', '#ffffff', '#ffffff', '#14213d')]
  ];

  var S = clone(DEF), logoData = null, view = 'both', zone = 'body', tab = 'items';
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (m) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]; }); }
  function colorName(h) { for (var i = 0; i < PALETTE.length; i++) if (PALETTE[i][1] === h.toLowerCase()) return PALETTE[i][0]; return ''; }
  function lum(h) { var n = parseInt(h.slice(1), 16); return (0.299 * (n >> 16) + 0.587 * (n >> 8 & 255) + 0.114 * (n & 255)) / 255; }
  function shade(h, k) { var n = parseInt(h.slice(1), 16), f = function (v) { return Math.max(0, Math.min(255, Math.round(v * k))); }; return '#' + ((1 << 24) + (f(n >> 16) << 16) + (f(n >> 8 & 255) << 8) + f(n & 255)).toString(16).slice(1); }
  function items() { return S.m === 'kit' ? ORDER.filter(function (i) { return S.k.indexOf(i) >= 0; }) : [S.g]; }
  function has(t) { return items().some(function (i) { return ITEMS[i].t === t || i === t; }); }
  function fontDef() { for (var i = 0; i < FONTS.length; i++) if (FONTS[i][0] === S.font) return FONTS[i]; return FONTS[0]; }
  function mirror(s) { return s + '<g transform="translate(400 0) scale(-1 1)">' + s + '</g>'; }

  /* ================= геометрия ================= */
  function bodyPath(ny) { return 'M118,52 C138,46 152,38 162,32 Q200,' + ny + ' 238,32 C248,38 262,46 282,52 C292,92 296,122 298,152 C297,240 300,330 304,424 Q200,448 96,424 C100,330 103,240 102,152 C104,122 108,92 118,52 Z'; }
  function tankPath(ny) { return 'M146,34 L166,32 Q200,' + (ny + 10) + ' 234,32 L254,34 C256,92 272,128 298,152 C297,240 300,330 304,424 Q200,448 96,424 C100,330 103,240 102,152 C128,128 144,92 146,34 Z'; }
  var TEE_SL = 'M120,52 C96,58 62,80 30,122 L68,184 C82,170 94,160 104,154 C104,122 110,88 120,52 Z';
  var TEE_CUFF = 'M30,122 L68,184 L77,177 L40,114 Z';
  var LONG_SL = 'M120,52 C94,60 72,96 62,156 C52,240 44,330 38,410 L84,414 C90,330 97,248 104,168 C104,122 110,88 120,52 Z';
  var LONG_CUFF = 'M38,410 L84,414 L86,390 L41,386 Z';
  var SIDE = 'M101,160 L117,162 L117,446 L95,440 Z';

  function patternShapes(id) {
    var c = S.c.pat, o = '';
    switch (S.p) {
      case 'stripes': for (var x = 118; x < 300; x += 44) o += '<rect x="' + x + '" y="-40" width="20" height="500" fill="' + c + '"/>'; break;
      case 'hoops': for (var y = 150; y < 450; y += 60) o += '<rect x="90" y="' + y + '" width="220" height="30" fill="' + c + '"/>'; break;
      case 'sash': o = '<path d="M90,20 L168,20 L312,340 L312,450 Z" fill="' + c + '"/>'; break;
      case 'halves': o = '<rect x="200" y="-40" width="112" height="500" fill="' + c + '"/>'; break;
      case 'grad': o = '<rect x="90" y="-40" width="222" height="500" fill="url(#' + id + 'g)"/>'; break;
      case 'chevron': o = '<path d="M90,176 L200,240 L310,176 L310,218 L200,282 L90,218 Z" fill="' + c + '"/>'; break;
      case 'yoke': o = '<path d="M90,-40 L310,-40 L310,134 Q200,168 90,134 Z" fill="' + c + '"/>'; break;
      case 'pin': for (var px = 108; px < 300; px += 16) o += '<rect x="' + px + '" y="-40" width="3" height="500" fill="' + c + '"/>'; break;
      case 'geo':
        var seed = 7, rnd = function () { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
        for (var gy = 20; gy < 450; gy += 46) for (var gx = 90; gx < 310; gx += 46)
          o += '<path d="M' + gx + ',' + gy + ' l46,0 l-46,46 Z" fill="' + c + '" opacity="' + (rnd() * .8).toFixed(2) + '"/><path d="M' + (gx + 46) + ',' + gy + ' l0,46 l-46,0 Z" fill="' + c + '" opacity="' + (rnd() * .8).toFixed(2) + '"/>';
        break;
    }
    return o;
  }
  function txt(x, y, size, fill, s, strokeW, extra) {
    var f = fontDef();
    return '<text x="' + x + '" y="' + y + '" font-family="' + f[2] + '" font-weight="' + f[3] + '" text-anchor="middle" font-size="' + size.toFixed(1) + '" fill="' + fill + '"' +
      (S.ow && strokeW ? ' stroke="' + S.c.outl + '" stroke-width="' + strokeW + '" paint-order="stroke" stroke-linejoin="round"' : '') + (extra || '') + '>' + esc(s) + '</text>';
  }
  function fit(s, max, room) { return Math.min(max, room / Math.max(s.length, 1) * 1.6); }
  var STITCH = ' fill="none" stroke="#000" stroke-opacity=".16" stroke-width="1.2" stroke-dasharray="4 3"';
  var EDGE = ' fill="none" stroke="#0b0d12" stroke-opacity=".2" stroke-width="1.4"';

  function topSVG(type, side, id) {
    var c = S.c, front = side === 'front';
    var tank = type === 'tank', longS = ['long', 'sweat', 'hoodie', 'jacket'].indexOf(type) >= 0, rib = type === 'sweat' || type === 'hoodie';
    var ny = front ? (type === 'jacket' ? 48 : type === 'polo' ? 60 : 66) : 46;
    var body = tank ? tankPath(ny) : bodyPath(ny), o = '';
    o += '<defs><clipPath id="' + id + 'b"><path d="' + body + '"/></clipPath>' +
      '<linearGradient id="' + id + 'g" x1="0" y1="0" x2="0" y2="1"><stop offset=".1" stop-color="' + c.pat + '" stop-opacity="0"/><stop offset="1" stop-color="' + c.pat + '"/></linearGradient></defs>';
    // рукава
    if (!tank) {
      var sl = longS ? LONG_SL : TEE_SL, cf = longS ? LONG_CUFF : TEE_CUFF;
      o += mirror('<path d="' + sl + '" fill="' + c.sleeve + '"/><path d="' + sl + '" fill="url(#vxShade)"/><path d="' + cf + '" fill="' + (rib ? c.trim : c.trim) + '"/>' +
        (rib ? '<path d="M44,394 L85,398" stroke="#000" stroke-opacity=".15"/>' : '') +
        '<path d="' + sl + '"' + EDGE + '/>' + (longS ? '<path d="M70,200 C66,240 62,280 58,330" fill="none" stroke="#000" stroke-opacity=".08" stroke-width="6" stroke-linecap="round"/>' : ''));
    }
    // капюшон сзади (на спине — поверх корпуса), спереди — за горловиной
    if (type === 'hoodie' && front) o += '<path d="M146,46 C128,0 160,-38 200,-38 C240,-38 272,0 254,46 Z" fill="' + c.body + '"/><path d="M146,46 C128,0 160,-38 200,-38 C240,-38 272,0 254,46 Z" fill="url(#vxShade)"/>';
    if (front && !tank && type !== 'jacket') o += '<path d="M162,32 Q200,18 238,32 Q200,' + ny + ' 162,32 Z" fill="' + shade(c.trim, .7) + '"/>';
    // корпус
    o += '<path d="' + body + '" fill="' + c.body + '"/>';
    var pat = patternShapes(id);
    if (pat) o += '<g clip-path="url(#' + id + 'b)"><g' + (front ? '' : ' transform="translate(400 0) scale(-1 1)"') + '>' + pat + '</g></g>';
    o += '<g clip-path="url(#' + id + 'b)">' + mirror('<path d="' + SIDE + '" fill="' + c.side + '"/>') +
      (rib ? '<rect x="80" y="404" width="240" height="50" fill="' + c.trim + '"/><g stroke="#000" stroke-opacity=".12">' + ribLines(96, 304, 410, 444) + '</g>' : '') +
      (type === 'jacket' ? '<rect x="80" y="412" width="240" height="40" fill="' + c.trim + '"/>' : '') + '</g>';
    o += '<path d="' + body + '" fill="url(#vxShade)"/>';
    // складки
    o += '<g fill="none" stroke="#000" stroke-opacity=".07" stroke-width="5" stroke-linecap="round"><path d="M130,200 C140,260 132,330 140,400"/><path d="M272,190 C262,250 270,320 262,400"/></g>';
    // ворот
    if (tank) {
      o += '<path d="' + body + '" fill="none" stroke="' + c.trim + '" stroke-width="7" clip-path="url(#' + id + 'b)"/>';
    } else if (type === 'polo') {
      if (front) o += '<path d="M188,60 L212,60 L212,150 L188,150 Z" fill="' + c.trim + '"/><circle cx="200" cy="86" r="3.4" fill="#fff" stroke="#000" stroke-opacity=".3"/><circle cx="200" cy="118" r="3.4" fill="#fff" stroke="#000" stroke-opacity=".3"/>' +
        mirror('<path d="M162,32 C156,40 148,46 140,50 L176,98 L200,62 Q178,54 162,32 Z" fill="' + c.trim + '"/><path d="M162,32 C156,40 148,46 140,50 L176,98 L200,62"' + EDGE + '/>');
      else o += '<path d="M160,32 Q200,46 240,32 L246,14 Q200,28 154,14 Z" fill="' + c.trim + '"/>';
    } else if (type === 'jacket') {
      o += '<path d="M156,42 C155,26 158,16 164,8 L236,8 C242,16 245,26 244,42 Q200,' + (front ? 56 : 50) + ' 156,42 Z" fill="' + c.trim + '"/><path d="M156,42 C155,26 158,16 164,8 L236,8 C242,16 245,26 244,42"' + EDGE + '/>';
      if (front) o += '<path d="M200,10 L200,436" stroke="' + shade(c.trim, .6) + '" stroke-width="4"/><path d="M200,10 L200,436" stroke="#fff" stroke-opacity=".35" stroke-width="1.2" stroke-dasharray="2 2"/><rect x="195" y="58" width="10" height="20" rx="3" fill="#c7cbd3"/>' +
        mirror('<path d="M126,300 L150,352"' + EDGE + ' stroke-width="2"/>');
    } else {
      o += front ? '<path d="M162,32 Q200,' + ny + ' 238,32 L247,36 Q200,' + (ny + 14) + ' 153,36 Z" fill="' + c.trim + '"/>'
        : '<path d="M162,32 Q200,46 238,32 L245,38 Q200,58 155,38 Z" fill="' + c.trim + '"/>';
    }
    if (type === 'hoodie') {
      if (front) o += '<path d="M146,46 C140,20 156,-6 172,-14 C190,-22 210,-22 228,-14 C244,-6 260,20 254,46 L238,32 Q200,72 162,32 Z" fill="' + c.body + '"/><path d="M162,32 C160,0 180,-20 200,-20 C220,-20 240,0 238,32 Q200,72 162,32 Z" fill="' + shade(c.trim, .75) + '"/>' +
        '<path d="M186,66 L182,150 M214,66 L218,150" stroke="' + c.trim + '" stroke-width="3" stroke-linecap="round"/>' +
        '<path d="M136,300 L264,300 L286,396 L114,396 Z" fill="#000" fill-opacity=".05" stroke="#000" stroke-opacity=".22"/><path d="M136,300 L118,370 M264,300 L282,370"' + STITCH + '/>';
      else o += '<path d="M146,46 C132,-4 166,-36 200,-36 C234,-36 268,-4 254,46 C250,112 228,146 200,148 C172,146 150,112 146,46 Z" fill="' + c.body + '"/><path d="M146,46 C132,-4 166,-36 200,-36 C234,-36 268,-4 254,46 C250,112 228,146 200,148 C172,146 150,112 146,46 Z" fill="url(#vxShade)"/>' +
        '<path d="M200,-36 L200,148" stroke="#000" stroke-opacity=".14"/><path d="M146,46 C132,-4 166,-36 200,-36 C234,-36 268,-4 254,46 C250,112 228,146 200,148 C172,146 150,112 146,46 Z"' + EDGE + '/>';
    }
    o += '<g' + STITCH + '><path d="M104,410 Q200,432 296,410"/>' + (tank ? '' : '<path d="M118,54 Q106,100 103,150"/><path d="M282,54 Q294,100 297,150"/>') + '</g>';
    o += '<path d="' + body + '"' + EDGE + '/>';
    // нанесения
    var f = fontDef();
    if (front) {
      var team = (S.team || '').toUpperCase();
      if (team && type !== 'jacket') o += txt(200, S.fnum ? 182 : 200, fit(team, 30, 230), c.text, team, 2.5, ' letter-spacing="1"');
      if (S.fnum && S.num && type !== 'jacket') o += txt(200, 252, 56 * f[4], c.num, S.num, 4);
      o += logoEl(id, S.lx, S.ly, S.ls, c.text);
    } else {
      var dy = type === 'hoodie' ? 44 : 0, nm = (S.name || '').toUpperCase();
      if (type === 'jacket') { if (team || S.team) o += txt(200, 150, fit(S.team.toUpperCase(), 40, 260), c.text, S.team.toUpperCase(), 3, ' letter-spacing="2"'); }
      else {
        if (nm) o += txt(200, 128 + dy, fit(nm, 28, 230), c.text, nm, 2.5, ' letter-spacing="2"');
        if (S.num) o += txt(200, 278 + dy, 118 * f[4], c.num, S.num, 6);
      }
    }
    return o;
  }
  function ribLines(x1, x2, y1, y2) { var s = ''; for (var x = x1; x < x2; x += 8) s += '<path d="M' + x + ',' + y1 + ' L' + x + ',' + y2 + '"/>'; return s; }
  function logoEl(id, x, y, s, col) {
    if (logoData) return '<image class="drag" data-logo="1" href="' + logoData + '" x="' + (x - s / 2) + '" y="' + (y - s / 2) + '" width="' + s + '" height="' + s + '" preserveAspectRatio="xMidYMid meet"/>';
    return '<g class="drag ph-logo" data-logo="1" opacity=".5"><rect x="' + (x - s / 2) + '" y="' + (y - s / 2) + '" width="' + s + '" height="' + s + '" rx="7" fill="none" stroke="' + col + '" stroke-width="1.4" stroke-dasharray="4 3"/><text x="' + x + '" y="' + (y + 3) + '" font-family="Inter Tight, sans-serif" font-size="' + Math.max(7, s / 5.5).toFixed(1) + '" font-weight="700" text-anchor="middle" fill="' + col + '">ЛОГО</text></g>';
  }

  function shortsSVG(side) {
    var c = S.c, f = fontDef(), o = '';
    var B = 'M82,22 L318,22 C326,110 336,200 346,288 Q282,302 214,292 L200,168 L186,292 Q118,302 54,288 C64,200 74,110 82,22 Z';
    o += '<path d="' + B + '" fill="' + c.bottom + '"/>';
    o += mirror('<path d="M81,50 L96,50 C88,130 80,210 72,294 L56,290 C64,210 72,130 81,50 Z" fill="' + c.side + '"/>');
    o += '<path d="' + B + '" fill="url(#vxShade)"/><path d="M82,22 L318,22 L320,50 L80,50 Z" fill="' + c.trim + '"/>';
    o += '<g stroke="#000" stroke-opacity=".1">' + ribLines(90, 316, 26, 46) + '</g>';
    if (side === 'front') o += '<path d="M194,50 Q190,74 184,82 M206,50 Q210,74 216,82" stroke="#fff" stroke-opacity=".8" stroke-width="2" fill="none" stroke-linecap="round"/>';
    o += '<g fill="none" stroke="#000" stroke-opacity=".08" stroke-width="5" stroke-linecap="round"><path d="M200,168 C190,130 160,110 130,100"/><path d="M200,168 C210,130 240,110 270,100"/></g>';
    o += '<g' + STITCH + '><path d="M60,276 Q120,288 184,280"/><path d="M216,280 Q280,288 340,276"/></g><path d="' + B + '"' + EDGE + '/>';
    if (side === 'front' && S.snum && S.num) o += txt(122, 252, 44 * f[4], c.num, S.num, 3.5);
    return o;
  }
  function pantsSVG(side) {
    var c = S.c, o = '';
    var B = 'M84,22 L316,22 C328,200 334,460 332,742 L232,746 L208,216 L192,216 L168,746 L68,742 C66,460 72,200 84,22 Z';
    o += '<path d="' + B + '" fill="' + c.bottom + '"/>' + mirror('<path d="M82,50 L97,50 C90,300 84,520 84,744 L69,742 C68,520 73,300 82,50 Z" fill="' + c.side + '"/><path d="M68,714 L168,718 L168,746 L68,742 Z" fill="' + c.trim + '"/>');
    o += '<path d="' + B + '" fill="url(#vxShade)"/><path d="M84,22 L316,22 L318,52 L82,52 Z" fill="' + c.trim + '"/><g stroke="#000" stroke-opacity=".1">' + ribLines(92, 314, 26, 48) + '</g>';
    if (side === 'front') o += '<path d="M194,52 Q190,80 184,88 M206,52 Q210,80 216,88" stroke="#fff" stroke-opacity=".8" stroke-width="2" fill="none" stroke-linecap="round"/>' + mirror('<path d="M100,70 Q130,120 150,170"' + STITCH + '/>');
    o += '<g fill="none" stroke="#000" stroke-opacity=".07" stroke-width="6" stroke-linecap="round"><path d="M130,300 C124,420 128,560 122,700"/><path d="M270,300 C276,420 272,560 278,700"/><path d="M118,470 C130,480 150,480 160,474"/><path d="M282,470 C270,480 250,480 240,474"/></g>';
    o += '<path d="' + B + '"' + EDGE + '/>';
    return o;
  }
  function socksSVG() {
    var c = S.c;
    var K = 'M40,0 L120,0 L121,300 C122,330 134,348 170,360 C198,370 198,422 164,424 L72,424 C40,424 33,392 40,360 Z';
    var one = '<path d="' + K + '" fill="' + c.bottom + '"/><rect x="40" y="0" width="81" height="26" fill="' + c.trim + '"/><rect x="40" y="40" width="81" height="14" fill="' + c.side + '"/><rect x="40" y="62" width="81" height="7" fill="' + c.side + '"/>' +
      '<path d="M40,360 C33,392 40,424 72,424 L92,424 C72,410 64,384 66,356 Z" fill="' + c.trim + '"/><path d="M164,424 C198,422 198,370 170,360 C176,380 176,410 150,424 Z" fill="' + c.trim + '"/>' +
      '<path d="' + K + '" fill="url(#vxShade)"/><g stroke="#000" stroke-opacity=".1">' + ribLines(46, 120, 4, 22) + '</g><path d="' + K + '"' + EDGE + '/>';
    return '<g transform="translate(96 18)">' + one + '</g><g>' + one + '</g>';
  }
  function ballSVG(side, id) {
    var c = S.c, o = '<defs><clipPath id="' + id + 'c"><circle cx="200" cy="200" r="186"/></clipPath><radialGradient id="' + id + 'r" cx=".36" cy=".3" r=".8"><stop offset="0" stop-color="#fff" stop-opacity=".45"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".32"/></radialGradient></defs>';
    function pent(cx, cy, r, rot) { var p = []; for (var i = 0; i < 5; i++) { var a = (rot + i * 72 - 90) * Math.PI / 180; p.push((cx + r * Math.cos(a)).toFixed(1) + ',' + (cy + r * Math.sin(a)).toFixed(1)); } return 'M' + p.join(' L') + ' Z'; }
    var rot = side === 'front' ? 0 : 36, g = '';
    o += '<circle cx="200" cy="200" r="186" fill="' + c.body + '"/>';
    g += '<path d="' + pent(200, 200, 58, rot) + '" fill="' + c.trim + '"/>';
    for (var i = 0; i < 5; i++) {
      var a = (rot + i * 72 + 90) * Math.PI / 180, x = 200 + 160 * Math.cos(a), y = 200 + 160 * Math.sin(a);
      g += '<path d="' + pent(x, y, 54, rot + 36 + i * 72) + '" fill="' + (S.p === 'plain' ? c.trim : c.pat) + '"/>';
      var a2 = (rot + i * 72 - 90) * Math.PI / 180;
      g += '<path d="M' + (200 + 58 * Math.cos(a2)).toFixed(1) + ',' + (200 + 58 * Math.sin(a2)).toFixed(1) + ' L' + (200 + 120 * Math.cos(a2)).toFixed(1) + ',' + (200 + 120 * Math.sin(a2)).toFixed(1) + '" stroke="#000" stroke-opacity=".18" stroke-width="1.5"/>';
    }
    o += '<g clip-path="url(#' + id + 'c)">' + g + '</g>';
    if (side === 'front' && logoData) o += '<image href="' + logoData + '" x="170" y="170" width="60" height="60" preserveAspectRatio="xMidYMid meet"/>';
    else if (S.team) o += '<text x="200" y="' + (side === 'front' ? 296 : 300) + '" font-family="Inter Tight, sans-serif" font-weight="900" font-size="' + fit(S.team.toUpperCase(), 24, 160).toFixed(1) + '" text-anchor="middle" fill="' + (lum(c.body) > .6 ? '#0b0d12' : '#ffffff') + '" letter-spacing="1">' + esc(S.team.toUpperCase()) + '</text>';
    o += '<circle cx="200" cy="200" r="186" fill="url(#' + id + 'r)"/><circle cx="200" cy="200" r="186"' + EDGE + '/>';
    return o;
  }
  function itemInner(type, side, id) {
    if (ITEMS[type].t === 'top') return topSVG(type, side, id);
    if (type === 'shorts') return shortsSVG(side);
    if (type === 'pants') return pantsSVG(side);
    if (type === 'socks') return socksSVG();
    return ballSVG(side, id);
  }
  var SHADE = '<linearGradient id="vxShade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".18"/><stop offset=".16" stop-color="#000" stop-opacity="0"/><stop offset=".4" stop-color="#fff" stop-opacity=".1"/><stop offset=".58" stop-color="#fff" stop-opacity="0"/><stop offset=".86" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".18"/></linearGradient>';

  /* ================= композиция сцены ================= */
  function nested(e, x, y, w, uid) {
    var it = ITEMS[e.id], vb = it.vb, h = w * vb[3] / vb[2];
    return { h: h, s: '<svg x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + h.toFixed(1) + '" viewBox="' + vb.join(' ') + '" overflow="visible">' + itemInner(e.id, e.side, uid) + '</svg>' };
  }
  function itemH(id) { var it = ITEMS[id]; return it.dw * it.vb[3] / it.vb[2]; }
  // колонки: «образ» (верх + низ) для каждой стороны + дополнительные изделия
  function columns(perRow) {
    var list = items(), sides = view === 'both' ? ['front', 'back'] : [view];
    var tops = list.filter(function (i) { return ITEMS[i].t === 'top'; }), bots = list.filter(function (i) { return ITEMS[i].t === 'bottom'; }), accs = list.filter(function (i) { return ITEMS[i].t === 'acc'; });
    var cols = [], single = list.length === 1;
    sides.forEach(function (sd) {
      var st = []; if (tops[0]) st.push({ id: tops[0], side: sd }); if (bots[0]) st.push({ id: bots[0], side: sd });
      if (st.length) cols.push({ stack: st, label: (single || sides.length > 1 ? (sd === 'front' ? 'Перед' : 'Спина') : ITEMS[st[0].id].n + (st[1] ? ' + ' + ITEMS[st[1].id].n.toLowerCase() : '')) });
    });
    tops.slice(1).concat(bots.slice(1)).forEach(function (id) { sides.forEach(function (sd) { cols.push({ stack: [{ id: id, side: sd }], label: ITEMS[id].n + (sides.length > 1 ? (sd === 'front' ? ' · перед' : ' · спина') : '') }); }); });
    accs.forEach(function (id) {
      var ss = id === 'ball' && single ? sides : [sides[0]];
      ss.forEach(function (sd) { cols.push({ stack: [{ id: id, side: sd }], label: ITEMS[id].n + (id === 'ball' && single && ss.length > 1 ? (sd === 'front' ? ' · вид 1' : ' · вид 2') : ''), acc: true }); });
    });
    // одиночный низ/аксессуар — крупнее
    var k = 1;
    if (!tops.length) k = bots.length ? 1.6 : 2.2;
    cols.forEach(function (c) {
      c.k = c.acc && (tops.length || bots.length) ? 1 : k;
      c.w = Math.max.apply(null, c.stack.map(function (e) { return ITEMS[e.id].dw * c.k; }));
      c.h = c.stack.reduce(function (a, e, i) { return a + itemH(e.id) * c.k - (i ? 34 : 0); }, 0);
    });
    var rows = []; for (var i = 0; i < cols.length; i += perRow) rows.push(cols.slice(i, i + perRow));
    return rows;
  }
  var GAP = 70, LBL = 44, PAD = 40;
  function composeSVG(perRow, extra) {
    var rows = columns(perRow), W = 0, H = PAD, body = '', n = 0;
    rows.forEach(function (r) { W = Math.max(W, r.reduce(function (a, c) { return a + c.w; }, 0) + GAP * (r.length - 1)); });
    W += PAD * 2;
    rows.forEach(function (r) {
      var rw = r.reduce(function (a, c) { return a + c.w; }, 0) + GAP * (r.length - 1), rh = Math.max.apply(null, r.map(function (c) { return c.h; }));
      var x = (W - rw) / 2;
      r.forEach(function (c) {
        var y = H + (rh - c.h) / (c.acc ? 1 : 2), parts = [];
        c.stack.forEach(function (e, i) {
          var w = ITEMS[e.id].dw * c.k, nx = x + (c.w - w) / 2, nd = nested(e, nx, y, w, 'u' + (n++));
          parts.push(nd.s); y += nd.h - 34;
        });
        body += '<g filter="url(#vxDrop)">' + parts.reverse().join('') + '</g>';
        body += '<text x="' + (x + c.w / 2) + '" y="' + (H + rh + 32) + '" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="15" letter-spacing="1.5" fill="#8a909c">' + esc(c.label.toUpperCase()) + '</text>';
        x += c.w + GAP;
      });
      H += rh + LBL + 30;
    });
    H += PAD - 30;
    return { w: W, h: H, s: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W.toFixed(0) + ' ' + H.toFixed(0) + '" width="' + W.toFixed(0) + '" height="' + H.toFixed(0) + '" preserveAspectRatio="xMidYMid meet">' + (extra || '') +
      '<defs>' + SHADE + '<filter id="vxDrop" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="16" stdDeviation="14" flood-color="#0b0d12" flood-opacity=".16"/></filter></defs>' + body + '</svg>' };
  }

  /* ================= рендер ================= */
  function perRow() { var w = $('#kc-canvas').clientWidth; return w < 520 ? 2 : w < 900 ? 3 : 4; }
  function render() {
    if (document.activeElement && document.activeElement.closest && document.activeElement.closest('#constructor')) dirty = true;
    $('#kc-canvas').innerHTML = composeSVG(perRow()).s;
    $('#kc-hint').style.visibility = has('top') && view !== 'back' ? 'visible' : 'hidden';
    bindDrag();
    renderControls();
    renderSummary();
    saveHash();
  }
  function chip(label, on, attr) { return '<button type="button" class="chip-b' + (on ? ' on' : '') + '" ' + attr + '>' + label + '</button>'; }
  function thumb(id) {
    var it = ITEMS[id], vb = it.vb;
    return '<svg viewBox="' + vb.join(' ') + '" preserveAspectRatio="xMidYMid meet"><defs>' + SHADE + '</defs>' + itemInner(id, 'front', 't' + id).replace(/<g class="drag[\s\S]*?<\/g>|<image class="drag"[^>]*\/>/, '') + '</svg>';
  }
  function renderControls() {
    $$('#kc-seg-mode button').forEach(function (b) { b.classList.toggle('on', b.dataset.m === S.m); });
    $('#kc-items').className = 'items' + (S.m === 'one' ? ' one' : '');
    $('#kc-items-tip').textContent = S.m === 'kit' ? 'Отметьте всё, что войдёт в комплект — цвета и дизайн применятся ко всем изделиям.' : 'Выберите изделие — покажем его крупно спереди и сзади.';
    $('#kc-items').innerHTML = ORDER.map(function (id) {
      var on = S.m === 'kit' ? S.k.indexOf(id) >= 0 : S.g === id;
      return '<button type="button" class="it' + (on ? ' on' : '') + '" data-i="' + id + '">' + thumb(id) + ITEMS[id].n + '</button>';
    }).join('');
    $('#kc-fonts').innerHTML = FONTS.map(function (f) { return chip('<span style="font-family:' + f[2] + ';font-weight:' + f[3] + ';font-size:15px">' + f[1].split(' ')[0] + ' 10</span>', S.font === f[0], 'data-f="' + f[0] + '"'); }).join('');
    $('#kc-logopos').innerHTML = LOGOPOS.map(function (l) { return chip(l[1], false, 'data-lp="' + l[0] + '"'); }).join('');
    $('#kc-patterns').innerHTML = PATTERNS.map(function (p) {
      var keep = S.p; S.p = p[0];
      var sv = '<svg viewBox="90 30 220 220"><defs><clipPath id="pi' + p[0] + '"><rect x="90" y="30" width="220" height="220"/></clipPath><linearGradient id="pi' + p[0] + 'g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + S.c.pat + '" stop-opacity="0"/><stop offset="1" stop-color="' + S.c.pat + '"/></linearGradient></defs><rect x="90" y="30" width="220" height="220" fill="' + S.c.body + '"/><g clip-path="url(#pi' + p[0] + ')">' + patternShapes('pi' + p[0]) + '</g></svg>';
      S.p = keep;
      return '<button type="button" class="pat' + (S.p === p[0] ? ' on' : '') + '" data-p="' + p[0] + '">' + sv + '<span>' + p[1] + '</span></button>';
    }).join('');
    var zs = activeZones(); if (zs.indexOf(zone) < 0) zone = zs[0];
    $('#kc-zones').innerHTML = zs.map(function (k) { return '<button type="button" class="zone' + (k === zone ? ' on' : '') + '" data-z="' + k + '" title="' + (ZONE_HELP[k] || '') + '"><i style="background:' + S.c[k] + '"></i>' + ZONES[k] + '</button>'; }).join('');
    var cur = S.c[zone].toLowerCase();
    $('#kc-palette').innerHTML = PALETTE.map(function (p) { return '<button type="button" class="sw-b' + (p[1] === cur ? ' on' : '') + '" style="background:' + p[1] + '" title="' + p[0] + '" data-c="' + p[1] + '"></button>'; }).join('');
    $('#kc-c-picker').value = cur;
    if (document.activeElement !== $('#kc-c-hex')) $('#kc-c-hex').value = cur.toUpperCase();
    setVal('#kc-f-team', S.team); setVal('#kc-f-name', S.name); setVal('#kc-f-num', S.num);
    $('#kc-f-fnum').checked = !!S.fnum; $('#kc-f-snum').checked = !!S.snum; $('#kc-f-outl').checked = !!S.ow;
    $('#kc-f-lsize').value = S.ls; $('#kc-logo-rm').hidden = !logoData;
    $$('#kc-tabs button').forEach(function (b) { b.classList.toggle('on', b.dataset.t === tab); });
    $$('.tab').forEach(function (t) { t.classList.toggle('on', t.dataset.tab === tab); });
  }
  function activeZones() {
    var top = has('top'), sl = items().some(function (i) { return ITEMS[i].t === 'top' && i !== 'tank'; }), low = has('bottom') || has('socks'), ball = has('ball');
    return Object.keys(ZONES).filter(function (k) {
      if (k === 'body') return top || ball; if (k === 'sleeve') return sl; if (k === 'pat') return S.p !== 'plain' && (top || ball);
      if (k === 'bottom') return low; if (k === 'outl') return !!S.ow; if (k === 'side') return top || low;
      if (k === 'text' || k === 'num') return top || has('shorts') || ball; return true;
    });
  }
  function setVal(s, v) { var el = $(s); if (document.activeElement !== el) el.value = v; }
  function renderPresets() {
    $('#kc-presets').innerHTML = PRESETS.map(function (p, i) {
      var c = p[1].c;
      return '<button type="button" class="preset" data-pr="' + i + '"><svg viewBox="0 0 42 42"><circle cx="21" cy="21" r="20" fill="' + c.body + '" stroke="rgba(11,13,18,.12)"/><path d="M21 1a20 20 0 0 1 0 40z" fill="' + c.pat + '"/><circle cx="21" cy="21" r="8" fill="' + c.bottom + '" stroke="#fff" stroke-width="2"/></svg>' + p[0] + '</button>';
    }).join('') + '<button type="button" class="preset" data-pr="rnd"><svg viewBox="0 0 42 42"><rect x="6" y="6" width="30" height="30" rx="8" fill="#0b0d12"/><circle cx="15" cy="15" r="3" fill="#fff"/><circle cx="27" cy="27" r="3" fill="#fff"/><circle cx="21" cy="21" r="3" fill="#fff"/><circle cx="27" cy="15" r="3" fill="#1f4bff"/><circle cx="15" cy="27" r="3" fill="#1f4bff"/></svg>Случайно</button>';
  }

  function summaryRows() {
    var rows = [], list = items();
    rows.push(['Изделия', list.map(function (i) { return ITEMS[i].n; }).join(', '), null, 1]);
    rows.push(['Рисунок', PATTERNS.filter(function (x) { return x[0] === S.p; })[0][1], null]);
    rows.push(['Шрифт', fontDef()[1], null]);
    activeZones().forEach(function (k) { var n = colorName(S.c[k]); rows.push([ZONES[k], S.c[k].toUpperCase() + (n ? ' ' + n.toLowerCase() : ''), S.c[k]]); });
    var top = has('top');
    if (top || has('ball')) rows.push(['Надпись', (S.team || '—').toUpperCase(), null]);
    if (top) rows.push(['Фамилия', (S.name || '—').toUpperCase(), null]);
    rows.push(['Номер', (S.num || '—') + (S.fnum && top ? ', на груди' : '') + (S.snum && has('shorts') ? ', на шортах' : ''), null]);
    if (top) rows.push(['Логотип', logoData ? 'есть (файл отправлю отдельно)' : 'нет', null, 1]);
    return rows;
  }
  function renderSummary() {
    $('#kc-summary').innerHTML = '<div class="sum">' + summaryRows().map(function (r) {
      return '<div class="sum-i' + (r[3] ? ' sum-w' : '') + '">' + (r[2] ? '<i style="background:' + r[2] + '"></i>' : '') + '<span>' + r[0] + ':</span><code title="' + esc(r[1]) + '">' + esc(r[1]) + '</code></div>';
    }).join('') + '</div>';
  }
  function summaryText() {
    return 'Здравствуйте! Хочу заказать форму Vaxter Five.\n' + summaryRows().map(function (r) { return '• ' + r[0] + ': ' + r[1]; }).join('\n') + '\nЭскиз: ' + link();
  }

  /* ================= ссылка ================= */
  var hashT;
  function encodeState() { return btoa(unescape(encodeURIComponent(JSON.stringify(S)))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
  function link() { return location.origin + '/#k=' + encodeState(); }
  var dirty = false;
  function saveHash() { if (!dirty) return; clearTimeout(hashT); hashT = setTimeout(function () { history.replaceState(null, '', location.pathname + location.search + '#k=' + encodeState()); }, 150); }
  function loadHash() {
    var m = location.hash.match(/^#k=([\w-]+)/); if (!m) return; dirty = true;
    try {
      var b = m[1].replace(/-/g, '+').replace(/_/g, '/'); while (b.length % 4) b += '=';
      var o = JSON.parse(decodeURIComponent(escape(atob(b)))), n = clone(DEF);
      Object.keys(n).forEach(function (k) { if (k !== 'c' && k !== 'k' && o[k] !== undefined && typeof o[k] === typeof n[k]) n[k] = o[k]; });
      if (Array.isArray(o.k)) n.k = o.k.filter(function (i) { return ITEMS[i]; });
      if (!n.k.length) n.k = DEF.k.slice();
      if (!ITEMS[n.g]) n.g = 'tee';
      if (o.c) Object.keys(n.c).forEach(function (k) { if (/^#[0-9a-f]{6}$/i.test(o.c[k] || '')) n.c[k] = o.c[k].toLowerCase(); });
      S = n;
    } catch (e) { /* битая ссылка — по умолчанию */ }
  }

  /* ================= перетаскивание логотипа ================= */
  function bindDrag() {
    $$('#kc-canvas [data-logo]').forEach(function (el) {
      var svg = el.ownerSVGElement;
      el.addEventListener('pointerdown', function (e) {
        e.preventDefault();
        var pt = function (ev) { var p = svg.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY; return p.matrixTransform(el.getScreenCTM().inverse()); };
        var p0 = pt(e), st = { lx: S.lx, ly: S.ly };
        var move = function (ev) {
          var q = pt(ev), h = S.ls / 2;
          S.lx = Math.round(Math.max(118 + h, Math.min(282 - h, st.lx + q.x - p0.x)));
          S.ly = Math.round(Math.max(56 + h, Math.min(410 - h, st.ly + q.y - p0.y)));
          var r = el.tagName === 'image' ? el : el.querySelector('rect'), t = el.querySelector && el.querySelector('text');
          r.setAttribute('x', S.lx - h); r.setAttribute('y', S.ly - h);
          if (t) { t.setAttribute('x', S.lx); t.setAttribute('y', S.ly + 3); }
        };
        var up = function () { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); render(); };
        window.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
      });
    });
  }

  /* ================= PNG ================= */
  var fontCSS = null;
  function embedFonts() {
    if (fontCSS !== null) return Promise.resolve(fontCSS);
    var get = function (u) { return fetch(u).then(function (r) { if (!r.ok) throw r; return r.text(); }); };
    return Promise.all([get('/css/fonts.css'), get('/css/fonts-kc.css')]).then(function (t) {
      var css = t.join(' '), urls = css.match(/\/fonts\/[\w.-]+\.woff2/g) || [];
      return Promise.all(urls.map(function (u) {
        return fetch(u).then(function (r) { return r.blob(); }).then(function (bl) {
          return new Promise(function (res) { var fr = new FileReader(); fr.onload = function () { res([u, fr.result]); }; fr.readAsDataURL(bl); });
        });
      })).then(function (p) { p.forEach(function (x) { css = css.split('url(' + x[0] + ')').join('url(' + x[1] + ')'); }); return css; });
    }).then(function (c) { fontCSS = c; return c; }).catch(function () { fontCSS = ''; return ''; });
  }
  function loadImg(src) { return new Promise(function (res, rej) { var i = new Image(); i.onload = function () { res(i); }; i.onerror = rej; i.src = src; }); }
  function rr(x, c, y, w, h, r) { x.beginPath(); x.moveTo(c + r, y); x.arcTo(c + w, y, c + w, y + h, r); x.arcTo(c + w, y + h, c, y + h, r); x.arcTo(c, y + h, c, y, r); x.arcTo(c, y, c + w, y, r); x.closePath(); }
  function exportPNG() {
    toast('Готовим PNG…');
    var prevView = view; if (view !== 'both' && items().some(function (i) { return ITEMS[i].t !== 'acc'; })) view = 'both';
    var comp;
    return Promise.all([embedFonts(), document.fonts.ready]).then(function (r) {
      comp = composeSVG(4, r[0] ? '<style>' + r[0] + '</style>' : '');
      view = prevView;
      var s = comp.s.replace(/<g class="drag ph-logo"[\s\S]*?<\/g>/g, '');
      return Promise.all([loadImg('data:image/svg+xml;charset=utf-8,' + encodeURIComponent(s)), loadImg('/img/logo.png').catch(function () { return null; })]);
    }).then(function (imgs) {
      var W = 2400, x, cv = document.createElement('canvas');
      var sw = W - 240, sh = sw * comp.h / comp.w; if (sh > 1500) { sh = 1500; sw = sh * comp.w / comp.h; }
      var zones = summaryRows().filter(function (r) { return r[2]; }), zr = Math.ceil(zones.length / 6);
      var H = 380 + sh + 80 + zr * 100 + 110; cv.width = W; cv.height = H; x = cv.getContext('2d');
      x.fillStyle = '#f5f6f8'; x.fillRect(0, 0, W, H);
      var g = x.createRadialGradient(W / 2, 300, 100, W / 2, 300 + sh / 2, W * .7); g.addColorStop(0, '#ffffff'); g.addColorStop(1, '#e3e7ee');
      x.fillStyle = g; rr(x, 60, 180, W - 120, sh + 280, 40); x.fill();
      if (imgs[1]) { var lh = 64, lw = imgs[1].width * lh / imgs[1].height; x.drawImage(imgs[1], 70, 62, lw, lh); }
      x.textAlign = 'right'; x.fillStyle = '#8a909c'; x.font = '500 26px "JetBrains Mono", monospace';
      x.fillText('КОНСТРУКТОР ФОРМЫ · VAXTERFIVE.RU', W - 70, 92); x.fillText(new Date().toLocaleDateString('ru-RU'), W - 70, 134);
      x.textAlign = 'left'; x.fillStyle = '#0b0d12'; x.font = '900 64px "Inter Tight", sans-serif';
      x.fillText(((S.team ? S.team + ' · ' : '') + (S.m === 'kit' ? 'комплект' : ITEMS[S.g].n)).toUpperCase(), 110, 280);
      x.fillStyle = '#1f4bff'; x.font = '600 28px "Inter Tight", sans-serif';
      x.fillText(items().map(function (i) { return ITEMS[i].n; }).join(' · ') + (S.num ? '  ·  №' + S.num : '') + (S.name && has('top') ? ' ' + S.name.toUpperCase() : ''), 112, 330);
      x.drawImage(imgs[0], (W - sw) / 2, 390, sw, sh);
      var cy = 180 + sh + 280 + 50, colW = (W - 140) / 6;
      zones.forEach(function (r, i) {
        var px = 70 + (i % 6) * colW, py = cy + Math.floor(i / 6) * 100;
        x.fillStyle = r[2]; rr(x, px, py, 64, 64, 16); x.fill(); x.strokeStyle = 'rgba(11,13,18,.15)'; x.lineWidth = 2; x.stroke();
        x.fillStyle = '#8a909c'; x.font = '500 22px "Inter Tight", sans-serif'; x.fillText(r[0], px + 84, py + 24);
        x.fillStyle = '#0b0d12'; x.font = '500 24px "JetBrains Mono", monospace'; x.fillText(r[2].toUpperCase(), px + 84, py + 56);
      });
      x.fillStyle = '#8a909c'; x.font = '500 22px "Inter Tight", sans-serif'; x.textAlign = 'right';
      x.fillText('+7 (900) 474-30-00 · zakaz@vaxterfive.ru · Эскиз, не макет для печати', W - 70, H - 36);
      cv.toBlob(function (b) {
        var a = document.createElement('a'); a.href = URL.createObjectURL(b);
        a.download = 'vaxterfive-' + ((S.team || 'eskiz').replace(/[^\wА-Яа-яЁё-]+/g, '_')) + (S.num ? '-' + S.num : '') + '.png';
        document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(a.href); }, 3000);
        toast('PNG сохранён');
      }, 'image/png');
    }).catch(function (e) { view = prevView; console.warn(e); toast('Не удалось собрать PNG'); });
  }

  /* ================= UI ================= */
  var tT;
  function toast(t) { var el = $('#kc-toast'); el.textContent = t; el.classList.add('show'); clearTimeout(tT); tT = setTimeout(function () { el.classList.remove('show'); }, 2600); }
  function copy(text, ok) {
    // iOS / in-app browsers: clipboard write must start synchronously inside the click gesture.
    var done = function () { if (ok) toast(ok); };
    function fallback() {
      var t = document.createElement('textarea'); t.value = text; t.setAttribute('readonly', ''); t.style.cssText = 'position:fixed;top:0;left:0;opacity:0;font-size:16px';
      document.body.appendChild(t); t.focus(); t.select(); t.setSelectionRange(0, text.length);
      var r = false; try { r = document.execCommand('copy'); } catch (e) {} t.remove(); if (r) done(); return r;
    }
    if (navigator.clipboard && window.isSecureContext) {
      try { navigator.clipboard.writeText(text).then(done, fallback); return; } catch (e) {}
    }
    fallback();
  }
  function randomKit() {
    var pick = function () { return PALETTE[Math.floor(Math.random() * PALETTE.length)][1]; };
    var a = pick(), b = pick(); while (b === a) b = pick();
    var d = lum(a) > .6 ? '#0b0d12' : '#ffffff';
    S.p = PATTERNS[Math.floor(Math.random() * PATTERNS.length)][0];
    S.c = { body: a, sleeve: Math.random() > .5 ? a : b, trim: b, side: b, pat: b, bottom: Math.random() > .5 ? b : a, text: d, num: d, outl: lum(d) > .5 ? '#0b0d12' : '#ffffff' };
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest('button'); if (!t || !t.closest('#constructor')) return; dirty = true;
    var d = t.dataset;
    if (d.m) { S.m = d.m; render(); }
    else if (d.i) {
      if (S.m === 'kit') { var ix = S.k.indexOf(d.i); if (ix >= 0) { if (S.k.length > 1) S.k.splice(ix, 1); else toast('В комплекте должно быть хотя бы одно изделие'); } else S.k.push(d.i); }
      else S.g = d.i;
      render();
    }
    else if (d.t) { tab = d.t; renderControls(); }
    else if (d.f) { S.font = d.f; render(); }
    else if (d.p) { S.p = d.p; render(); }
    else if (d.z) { zone = d.z; renderControls(); }
    else if (d.c) { S.c[zone] = d.c; render(); }
    else if (d.pr !== undefined) { if (d.pr === 'rnd') randomKit(); else { var pr = clone(PRESETS[+d.pr][1]); S.p = pr.p; S.c = pr.c; } render(); }
    else if (d.lp) { S.lx = d.lp === 'l' ? 252 : d.lp === 'r' ? 148 : 200; S.ly = d.lp === 'c' ? (S.team ? 124 : 150) : 104; render(); }
    else if (d.v) { view = d.v; $$('#kc-seg-view button').forEach(function (b) { b.classList.toggle('on', b === t); }); render(); }
  });
  $('#kc-c-picker').addEventListener('input', function (e) { S.c[zone] = e.target.value; render(); });
  $('#kc-c-hex').addEventListener('input', function (e) { var v = e.target.value.trim(); if (v[0] !== '#') v = '#' + v; if (/^#[0-9a-f]{6}$/i.test(v)) { S.c[zone] = v.toLowerCase(); render(); } });
  $('#kc-f-team').addEventListener('input', function (e) { S.team = e.target.value; render(); });
  $('#kc-f-name').addEventListener('input', function (e) { S.name = e.target.value; render(); });
  $('#kc-f-num').addEventListener('input', function (e) { e.target.value = e.target.value.replace(/\D/g, ''); S.num = e.target.value; render(); });
  $('#kc-f-fnum').addEventListener('change', function (e) { S.fnum = e.target.checked ? 1 : 0; render(); });
  $('#kc-f-snum').addEventListener('change', function (e) { S.snum = e.target.checked ? 1 : 0; render(); });
  $('#kc-f-outl').addEventListener('change', function (e) { S.ow = e.target.checked ? 1 : 0; render(); });
  $('#kc-f-lsize').addEventListener('input', function (e) { S.ls = +e.target.value; render(); });
  $('#kc-f-logo').addEventListener('change', function (e) {
    var f = e.target.files[0]; if (!f) return;
    var fr = new FileReader();
    fr.onload = function () {
      loadImg(fr.result).then(function (im) {
        var k = Math.min(1, 600 / Math.max(im.width, im.height)), c = document.createElement('canvas');
        c.width = Math.round(im.width * k); c.height = Math.round(im.height * k); c.getContext('2d').drawImage(im, 0, 0, c.width, c.height);
        logoData = c.toDataURL('image/png'); render(); toast('Логотип добавлен — его можно перетащить');
      }).catch(function () { toast('Не удалось прочитать файл'); });
    };
    fr.readAsDataURL(f); e.target.value = '';
  });
  $('#kc-logo-rm').addEventListener('click', function () { logoData = null; render(); });
  $('#kc-btn-png').addEventListener('click', exportPNG);
    $('#kc-btn-link') && $('#kc-btn-link').addEventListener('click', function () { dirty = true; saveHash(); copy(link(), logoData ? 'Ссылка скопирована (без файла логотипа)' : 'Ссылка скопирована'); });
  $('#kc-btn-desc') && $('#kc-btn-desc').addEventListener('click', function () { copy(summaryText(), 'Описание скопировано'); });
  $('#kc-btn-send').addEventListener('click', function () { dirty = true; saveHash(); copy(link()); $('#kc-contact').click(); });
  $('#kc-btn-reset').addEventListener('click', function () { S = clone(DEF); logoData = null; render(); toast('Начинаем заново'); });
  var rT; window.addEventListener('resize', function () { clearTimeout(rT); rT = setTimeout(render, 150); });

  loadHash();
  if (dirty) setTimeout(function () { document.getElementById('constructor').scrollIntoView(); }, 300);
  renderPresets();
  render();
  if (document.fonts) Promise.all(['700 16px Oswald', '16px "Russo One"', '900 16px "Inter Tight"'].map(function (f) { return document.fonts.load(f, 'AБ10'); })).then(render, render);
  window.__kc = { state: function () { return S; } };
})();
