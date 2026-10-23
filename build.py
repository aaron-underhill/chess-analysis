"""Runs on Vercel during every deploy, before the site goes live.

1. Applies database migrations, so Neon's tables always match the models.
2. Imports any new Chess.com games. On the very first deploy this loads
   the full history, so the site never starts empty.

Vercel collects static files (CSS) on its own afterward.
"""

import os
import subprocess
import sys


def manage(*args):
    print("$ python manage.py", *args, flush=True)
    subprocess.run([sys.executable, "manage.py", *args], check=True)


def main():
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL isn't set, so skipping migrations and import.")
        return

    manage("migrate", "--noinput")

    username = os.environ.get("CHESSCOM_USERNAME")
    if username:
        try:
            manage("import_games", username)
        except subprocess.CalledProcessError:
            # A Chess.com outage shouldn't block a deploy; the daily
            # import will catch up.
            print("Import failed; continuing with the deploy.")


if __name__ == "__main__":
    main()
