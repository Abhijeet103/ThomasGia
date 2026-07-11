from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Import superusers and Google SocialApp records from the legacy SQLite database into the current database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-db",
            default="data/prepgia.sqlite3",
            help="Path to the source SQLite database file.",
        )

    def handle(self, *args, **options):
        source_path = Path(options["source_db"]).expanduser()
        if not source_path.exists():
            raise CommandError(f"Source SQLite database not found: {source_path}")

        source = sqlite3.connect(source_path)
        source.row_factory = sqlite3.Row
        try:
            self._import_from_sqlite(source)
        finally:
            source.close()

    @transaction.atomic
    def _import_from_sqlite(self, source: sqlite3.Connection) -> None:
        User = get_user_model()

        superuser_rows = source.execute(
            """
            SELECT *
            FROM accounts_user
            WHERE is_superuser = 1
            ORDER BY id
            """
        ).fetchall()

        imported_users = 0
        for row in superuser_rows:
            user, created = User.objects.update_or_create(
                email=row["email"],
                defaults={
                    "password": row["password"],
                    "last_login": row["last_login"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "is_superuser": bool(row["is_superuser"]),
                    "is_staff": bool(row["is_staff"]),
                    "is_active": bool(row["is_active"]),
                    "date_joined": row["date_joined"],
                    "role": row["role"] or "free",
                    "google_sub": row["google_sub"],
                    "subscription_expires_at": row["subscription_expires_at"],
                },
            )
            imported_users += 1
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} superuser: {user.email}")

        google_apps = source.execute(
            """
            SELECT *
            FROM socialaccount_socialapp
            WHERE provider = 'google'
            ORDER BY id
            """
        ).fetchall()

        imported_apps = 0
        for app_row in google_apps:
            linked_site_ids = [
                row["site_id"]
                for row in source.execute(
                    """
                    SELECT site_id
                    FROM socialaccount_socialapp_sites
                    WHERE socialapp_id = ?
                    ORDER BY site_id
                    """,
                    (app_row["id"],),
                ).fetchall()
            ]

            sites = []
            for site_id in linked_site_ids:
                site_row = source.execute(
                    "SELECT id, domain, name FROM django_site WHERE id = ?",
                    (site_id,),
                ).fetchone()
                if site_row is None:
                    continue
                site, _ = Site.objects.update_or_create(
                    id=site_row["id"],
                    defaults={
                        "domain": site_row["domain"],
                        "name": site_row["name"],
                    },
                )
                sites.append(site)

            app_settings = {}
            raw_settings = app_row["settings"]
            if raw_settings:
                try:
                    app_settings = json.loads(raw_settings)
                except json.JSONDecodeError as exc:
                    raise CommandError(
                        f"Could not decode settings JSON for SocialApp id={app_row['id']}"
                    ) from exc

            social_app, created = SocialApp.objects.update_or_create(
                provider="google",
                name=app_row["name"],
                defaults={
                    "client_id": app_row["client_id"],
                    "secret": app_row["secret"],
                    "key": app_row["key"] or "",
                    "provider_id": app_row["provider_id"] or "",
                    "settings": app_settings,
                },
            )
            social_app.sites.set(sites)
            imported_apps += 1
            action = "Created" if created else "Updated"
            site_list = ", ".join(site.domain for site in sites) or "no linked sites"
            self.stdout.write(f"{action} Google SocialApp: {social_app.name} ({site_list})")

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_users} superuser(s) and {imported_apps} Google SocialApp record(s) "
                f"from {source.execute('PRAGMA database_list').fetchone()['file']} into the current database."
            )
        )
        self.stdout.write(f"Current Django SITE_ID is {settings.SITE_ID}.")
