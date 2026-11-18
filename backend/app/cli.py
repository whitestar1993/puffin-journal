"""Small admin CLI.

    python -m app.cli hash-password     # prompts twice, prints an argon2 hash for APP_PASSWORD_HASH
    python -m app.cli secret-key        # prints a random SECRET_KEY
"""

import getpass
import secrets
import sys

from app.auth import hash_password


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "hash-password":
        pw = getpass.getpass("Password: ")
        if len(pw) < 8:
            print("Use at least 8 characters.", file=sys.stderr)
            return 1
        if getpass.getpass("Again: ") != pw:
            print("Passwords don't match.", file=sys.stderr)
            return 1
        h = hash_password(pw)
        print(h)
        print("\nPut it in .env inside single quotes:", file=sys.stderr)
        print(f"APP_PASSWORD_HASH='{h}'", file=sys.stderr)
        return 0
    if cmd == "secret-key":
        print(secrets.token_urlsafe(48))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
