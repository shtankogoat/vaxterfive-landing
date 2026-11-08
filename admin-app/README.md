# Админка каталога Vaxter Five

Веб-панель, через которую сотрудники сами ведут каталог (категории, товары, фото, значения по умолчанию)
без разработчика. Живёт по **секретному адресу** `https://vaxterfive.ru<ADMIN_PREFIX>` — например
`/vf-<32 случайных символа>/`. Адрес `/admin/` отвечает обычным 404.

Вход — фирменная страница входа по секретному адресу:
1. **Логин и пароль** сотрудника (длинный логин, пароль мин. 16 символов).
2. **Код 2FA** из Яндекс Ключа / Google Authenticator (обязателен для всех).

## Как это работает

1. Все правки сохраняются в **черновик** (`data/draft.json`); сайт не меняется. Вверху — жёлтая полоса
   «Есть неопубликованные изменения».
2. **«Опубликовать»**: проверка черновика (slug-и, уникальность, описание и фото у товаров, файлы фото
   существуют, в категории ≥ 1 товар) → копия текущего `catalog-src/catalog.json` в `data/backups/`
   (последние 50) → **атомарная** запись нового `catalog.json` (временный файл + fsync + rename) →
   `python catalog-src/build.py` пересобирает `catalog/` и `sitemap.xml`. Упала сборка — откат.
3. **«Версии»** — «Вернуть» сразу публикует выбранную копию (байт-в-байт). «Отменить» — выбросить черновик.
4. Фото сразу кладутся в `img/products/` под случайным именем; удалённое из товара фото физически
   остаётся (нужно для возврата старых версий).
5. На странице товара — ссылка «Страница на сайте ↗» (после публикации).

Роли: **администратор** — всё + пользователи (добавить/удалить, сбросить 2FA) + журнал;
**менеджер** — каталог, версии, свой пароль. Учётки обезличены: отображаемое имя администратора —
«Администратор», в журнале и уведомлениях — только логин.

Изменение в `catalog-src/build.py` (обратно совместимое, вывод байт-в-байт тот же): очищается
содержимое `catalog/`, а не папка целиком — админке не нужны права записи в корень сайта.

## Меры безопасности

| Мера | Как сделано |
|---|---|
| Секретный адрес | Всё приложение (страницы, статика, cookie) висит на `ADMIN_PREFIX`. Любой другой путь — `404 Not Found` текстом, без подсказок; `/admin` в nginx тоже 404. Это не замена паролю, а защита от сканеров. |
| Пароли | argon2id, **мин. 16 символов**, буквы + цифры/символы. Пароля по умолчанию нет — первый админ создаётся из консоли (`manage.py create-admin`). Хэш считается и для несуществующих логинов (нет утечки по времени). |
| 2FA (TOTP, RFC 6238) | Обязательна. Первый вход после пароля — принудительная настройка: QR рисуется на сервере (inline SVG, без внешних сервисов) + ключ для ручного ввода; подключение подтверждается кодом. Шаг 30 с, окно ±1 шаг. **Повтор кода запрещён** — хранится последний использованный шаг. Неверные коды считаются вместе с неверными паролями (лимит и блокировка). Пока 2FA не пройдена, сессии нет — только «ожидание кода» на 5 минут. Секреты TOTP в `users.json` **зашифрованы** (Fernet, ключ из `TOTP_ENC_KEY` или из `SECRET_KEY`); сам файл — chmod 600. Потерян телефон → админ жмёт «Сбросить 2FA» у пользователя или `manage.py reset-2fa <логин>`. |
| Сессии | Подписанная cookie `vf_admin`: `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=<ADMIN_PREFIX>`. `SECRET_KEY` — из env-файла (chmod 600), без него приложение не стартует. Бездействие 30 мин, максимум 8 ч. Сессия пересоздаётся при входе (защита от фиксации). Смена пароля, сброс 2FA, удаление пользователя мгновенно гасят его сессии. |
| CSRF | Токен в сессии проверяется на **каждом** POST (включая вход и 2FA); плюс SameSite=Strict. |
| Подбор | 5 неудач (пароль или код) на логин или 10 на IP за 15 минут → блокировка (429) — даже верный код не принимается. В `auth.log`: `LOGIN_FAIL` / `TOTP_FAIL` / `LOGIN_BLOCKED ip=… user=…` → fail2ban банит IP фаерволом. |
| Уведомления | Telegram на: успешный вход, неверный пароль, неверный код 2FA, блокировку, подключение/сброс 2FA, создание/удаление пользователя. Формат: `🔐 Vaxter admin: <событие>, логин <x>, IP <ip>, <браузер/ОС>, <время МСК>`. Отправка в фоновом потоке с таймаутом 8 с через `TELEGRAM_PROXY` — если Telegram недоступен, вход не тормозит и не падает. Без токена — ничего не шлёт, пишет `TG_SKIP` в `auth.log`. |
| Загрузка фото | Только jpg/jpeg/png/webp, ≤ 15 МБ, ≤ 10 за раз; файл реально открывается Pillow (verify + загрузка), защита от «пиксельных бомб». **Пере-кодирование**: поворот по EXIF, удаление EXIF/GPS, ≤ 2000 px, progressive JPEG. Имя `u-<16 hex>.jpg`, имя пользователя игнорируется; путь проверяется — только `img/products/`. |
| XSS / инъекции | Автоэкранирование Jinja2 (генератор сайта тоже экранирует). Строгий slug (`a-z0-9-`, ≤ 60, уникальность), лимиты длины, запрет управляющих символов, нет путей из пользовательского ввода. |
| Заголовки | CSP (`script-src 'self'`, без inline-скриптов, `frame-ancestors 'none'`), `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: same-origin`, `Permissions-Policy`, `Cache-Control: no-store`, `X-Robots-Tag: noindex` (+ meta), HSTS в nginx. |
| Изоляция | Системный пользователь `vfadmin` без shell; gunicorn только на `127.0.0.1:5600`. Запись — только `catalog-src/`, `catalog/`, `img/products/`, `sitemap.xml`, `/var/lib/vaxterfive-admin`; в systemd дополнительно `ProtectSystem=strict` + `ReadWritePaths`, `NoNewPrivileges`, пустые capabilities. |
| Журнал | `data/audit.log`: кто (логин), когда, IP, что сделал — входы, неудачи, 2FA, правки, публикации, восстановления, пользователи. Раздел «Журнал» у админа. |

## Локальный запуск (Windows)

```powershell
cd D:\Business\websites\vaxterfive\admin-app
pip install -r requirements.txt
python app.py      # адрес: http://127.0.0.1:5600<ADMIN_PREFIX>login
```
`.env` (локальный, не коммитить): `SECRET_KEY`, `SITE_ROOT`, `ADMIN_PREFIX`,
`COOKIE_SECURE=0` (только для http://127.0.0.1), `ADMIN_DEV=1` (раздаёт `/img`, `/css`, `/js`, `/catalog` для
превью; **на сервере не ставить**).

## Деплой на сервер (Ubuntu 24.04)

```bash
# 1. пользователь и папки
sudo useradd --system --no-create-home --shell /usr/sbin/nologin vfadmin
sudo mkdir -p /opt/vaxterfive-admin /var/lib/vaxterfive-admin
sudo rsync -a --exclude data --exclude .env --exclude screenshots ./admin-app/ /opt/vaxterfive-admin/
sudo chown -R root:root /opt/vaxterfive-admin                 # код — только чтение
sudo chown vfadmin:vfadmin /var/lib/vaxterfive-admin && sudo chmod 700 /var/lib/vaxterfive-admin

# 2. зависимости
sudo apt install -y python3-venv
sudo python3 -m venv /opt/vaxterfive-admin/venv
sudo /opt/vaxterfive-admin/venv/bin/pip install -r /opt/vaxterfive-admin/requirements.txt

# 3. права на запись в сайт
cd /var/www/vaxterfive
sudo chown -R vfadmin:www-data catalog-src catalog img/products sitemap.xml
sudo chmod -R u+rwX,g+rX,o+rX catalog-src catalog img/products sitemap.xml

# 4. env: секреты, свой ADMIN_PREFIX, Telegram
sudo cp /opt/vaxterfive-admin/deploy/vaxterfive-admin.env.example /etc/vaxterfive-admin.env
sudo chmod 600 /etc/vaxterfive-admin.env
python3 -c "import secrets;print(secrets.token_urlsafe(48))"        # → SECRET_KEY (и ещё раз → TOTP_ENC_KEY)
python3 -c "import secrets;print('/vf-'+secrets.token_hex(16)+'/')"  # → ADMIN_PREFIX
sudo nano /etc/vaxterfive-admin.env

# 5. первый администратор (пароль спросит; 2FA настроит при первом входе)
cd /opt/vaxterfive-admin && sudo -u vfadmin env $(sudo cat /etc/vaxterfive-admin.env | grep -v '^#' | xargs) venv/bin/python manage.py create-admin <логин>

# 6. сервис
sudo cp deploy/vaxterfive-admin.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now vaxterfive-admin

# 7. nginx: вставить deploy/nginx-admin.conf в server{} сайта, подставив ADMIN_PREFIX
sudo nginx -t && sudo systemctl reload nginx

# 8. fail2ban
sudo apt install -y fail2ban
sudo cp deploy/fail2ban-filter-vaxterfive-admin.conf /etc/fail2ban/filter.d/vaxterfive-admin.conf
sudo cp deploy/fail2ban-jail-vaxterfive-admin.conf /etc/fail2ban/jail.d/vaxterfive-admin.conf
sudo systemctl restart fail2ban
```
Один gunicorn-воркер (с потоками): лимиты попыток и блокировка публикации живут в памяти процесса.
Обновление: rsync в `/opt/vaxterfive-admin` (кроме data/.env) → `sudo systemctl restart vaxterfive-admin`.

**Telegram:** создать бота у @BotFather → `TELEGRAM_BOT_TOKEN`; написать боту, узнать chat id
(`https://api.telegram.org/bot<TOKEN>/getUpdates`) → `TELEGRAM_CHAT_IDS` (через запятую);
`TELEGRAM_PROXY=socks5h://user:pass@host:port` (нужен на сервере в РФ). Перезапустить сервис.

## Заявки с сайта → AmoCRM

Публичный маршрут `POST /api/lead` (единственный вне секретного адреса). Лендинг отправляет форму
`fetch('/api/lead', {method:'POST', body: new FormData(form)})` с того же домена.

**Запрос** (multipart/form-data):

| Поле | Обязательно | Правило |
|---|---|---|
| `what` | да | текст ≤ 2000 |
| `qty` | нет | целое 1…1 000 000 |
| `date` | нет | `ГГГГ-ММ-ДД` |
| `design` | нет | `Да` / `Нет` / `Есть пример` |
| `mat` | нет | `Знаю` / `Помощь` |
| `name` | да | ≤ 100 |
| `contact` | да | телефон (10–15 цифр, `+ ( ) -` и пробелы) или `@telegram` |
| `consent` | да | ровно `Да` |
| `website` | — | ловушка для ботов, должно быть пустым |
| `page` | нет | URL страницы |
| `kit` | нет | `https://vaxterfive.ru/#k=…` |
| `attachment` | нет | файл ≤ 10 МБ: jpg, png, webp, pdf, ai, cdr, psd, zip (проверяется сигнатура) |

**Ответ** (JSON): `200 {"ok":true}` · `400 {"ok":false,"error":"<текст для посетителя>"}` (ошибка проверки) ·
`403 {"ok":false,"error":"Запрос отклонён."}` (чужой Origin/Referer) · `413` (файл больше 10 МБ) ·
`429 {"ok":false,"error":"Слишком много заявок…"}` · `405` (не POST). При заполненной ловушке — `{"ok":true}`, но заявка не сохраняется.

Защита: Origin (или Referer) должен быть `https://vaxterfive.ru` / `https://www.vaxterfive.ru` (локально при `ADMIN_DEV=1` ещё `http://127.0.0.1:*`, `http://localhost:*`);
CORS-заголовков нет; лимит 5 заявок за 10 минут и 30 в сутки с одного IP (SQLite); строгая проверка полей и файлов.

Хранение (заявка не теряется): `data/leads.jsonl` (сырой журнал) + `data/leads.sqlite3` (статусы), файл — `data/lead-files/<uuid>.<ext>`.
Файлы отдаются **только** через админку: раздел «Заявки» — список (новые сверху), статус (в AMO / ошибка / не настроено),
скачивание вложения, кнопка «Отправить в AMO повторно».

AmoCRM (API v4, в фоновом потоке, таймаут 8 с): `POST /api/v4/leads/complex` — сделка «Заявка с сайта: …», контакт
(имя + телефон в поле PHONE; ник Telegram — только в примечании), теги «сайт», «vaxterfive.ru», при заданных env — воронка,
этап, ответственный; затем `POST /api/v4/leads/{id}/notes` — примечание со всеми полями, ссылкой конструктора,
ссылкой на файл в админке (нужен вход), страницей и IP.

Env: `AMO_SUBDOMAIN` (vaxterfive → https://vaxterfive.amocrm.ru), `AMO_TOKEN`, необязательные `AMO_PIPELINE_ID`,
`AMO_STATUS_ID`, `AMO_RESPONSIBLE_USER_ID`, `AMO_PROXY`, `SITE_URL`. (`AMO_BASE_URL` — только для тестов с поддельным сервером.)

**Как получить долгосрочный токен:** AmoCRM → Настройки → Интеграции → «Создать интеграцию» (внешняя) → отметить
доступ «Всё» → сохранить → вкладка «Ключи и доступы» → «Долгосрочный токен» → выбрать срок → скопировать в `AMO_TOKEN`.
ID воронки/этапа видны в адресной строке при настройке воронки (или `GET /api/v4/leads/pipelines`).
После правки env — `sudo systemctl restart vaxterfive-admin`. Ошибки отправки видны в «Заявки» и в `auth.log` (`LEAD_AMO_FAIL`).

## Пользователи

- В интерфейсе: администратор → «Пользователи»: добавить (логин, имя-роль, пароль ≥ 16, роль), удалить,
  **«Сбросить 2FA»** (потерян телефон). Пароль передать лично; 2FA сотрудник подключит при первом входе.
- Свой пароль — клик по имени в шапке.
- Консоль сервера (`M=` — для краткости):
  ```bash
  M="cd /opt/vaxterfive-admin && sudo -u vfadmin env $(sudo cat /etc/vaxterfive-admin.env | grep -v '^#' | xargs) /opt/vaxterfive-admin/venv/bin/python /opt/vaxterfive-admin/manage.py"
  $M add-user manager1            # менеджер
  $M add-user admin2 --admin      # администратор
  $M set-password manager1        # сброс пароля
  $M reset-2fa manager1           # сброс 2FA
  $M delete-user manager1
  $M list-users
  ```

## Файлы

- `app.py` — веб-приложение (маршруты, вход + 2FA, загрузка фото)
- `leads.py` — приём заявок, хранение, отправка в AmoCRM
- `throttle.py` — счётчики неудачных входов (SQLite)
- `security.py` — TOTP (шифрование секретов, QR), уведомления Telegram
- `store.py` — черновик, валидация, бэкапы, публикация, пользователи, аудит
- `manage.py` — CLI
- `templates/`, `static/` — интерфейс
- `deploy/` — systemd, nginx, fail2ban, пример env
- `data/` — (не в git) users.json (chmod 600), draft.json, backups/, audit.log, auth.log
