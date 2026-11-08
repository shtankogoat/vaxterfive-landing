"""CLI админки.
  python manage.py gen-secret                      — сгенерировать SECRET_KEY
  python manage.py create-admin <логин>            — создать администратора (пароль спросит)
  python manage.py add-user <логин> [--admin]      — создать пользователя
  python manage.py set-password <логин>            — сбросить пароль (если забыли)
  python manage.py delete-user <логин>
  python manage.py reset-2fa <логин>               — сбросить 2FA (потерян телефон)
  python manage.py list-users
Пароль можно передать через stdin: echo 'пароль' | python manage.py create-admin <логин> --password-stdin
"""
import getpass, os, secrets, sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
env = Path(os.environ.get("ADMIN_ENV_FILE", APP_DIR / ".env"))
if env.is_file():
    for line in env.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import store as S  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def ask_password():
    if "--password-stdin" in sys.argv:
        return sys.stdin.readline().rstrip("\r\n")
    p1 = getpass.getpass("Пароль (мин. 16 символов): ")
    if p1 != getpass.getpass("Ещё раз: "):
        sys.exit("Пароли не совпадают.")
    return p1


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "gen-secret":
        print(secrets.token_urlsafe(48))
        return
    S.ensure_dirs()
    if cmd == "list-users":
        for n, u in S.load_users().items():
            print(f"{n:28} {u['role']:8} 2FA:{'да' if u.get('totp_enc') else 'нет'}  {u.get('display', '')}")
        return
    if len(a) < 2:
        sys.exit(__doc__)
    name = a[1].strip().lower()
    try:
        if cmd in ("create-admin", "add-user"):
            role = "admin" if cmd == "create-admin" or "--admin" in sys.argv else "manager"
            S.create_user(name, ask_password(), role, "Администратор" if role == "admin" else "")
            S.audit("cli", "Добавлен пользователь", f"{name} ({role})")
            print(f"OK: создан {role} «{name}»")
        elif cmd == "set-password":
            if name not in S.load_users():
                sys.exit("Нет такого пользователя.")
            S.set_password(name, ask_password())
            S.audit("cli", "Сброшен пароль", name)
            print("OK: пароль изменён, все сессии пользователя завершены")
        elif cmd == "reset-2fa":
            if name not in S.load_users():
                sys.exit("Нет такого пользователя.")
            S.reset_totp(name)
            S.audit("cli", "Сброшена 2FA", name)
            print("OK: 2FA сброшена — при следующем входе пользователь настроит её заново")
        elif cmd == "delete-user":
            us = S.load_users()
            if us.pop(name, None) is None:
                sys.exit("Нет такого пользователя.")
            S.save_users(us)
            S.audit("cli", "Удалён пользователь", name)
            print("OK: удалён")
        else:
            sys.exit(__doc__)
    except ValueError as e:
        sys.exit(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
