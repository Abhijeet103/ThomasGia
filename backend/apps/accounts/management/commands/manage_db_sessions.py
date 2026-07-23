from __future__ import annotations

from urllib.parse import urlparse

import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "List or terminate PostgreSQL sessions using a direct admin connection."

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            help="List active sessions for the configured PostgreSQL database.",
        )
        parser.add_argument(
            "--terminate-all",
            action="store_true",
            help="Terminate all other sessions connected to the configured PostgreSQL database.",
        )

    def handle(self, *args, **options):
        if not options["list"] and not options["terminate_all"]:
            raise CommandError("Use either --list or --terminate-all.")

        admin_url = getattr(settings, "DATABASE_ADMIN_URL", "") or ""
        if not admin_url:
            raise CommandError(
                "DATABASE_ADMIN_URL is not configured. Use a direct PostgreSQL connection string, not the pooler URL."
            )

        parsed = urlparse(admin_url)
        hostname = parsed.hostname or ""
        if hostname.endswith("pooler.supabase.com"):
            raise CommandError(
                "DATABASE_ADMIN_URL points to the Supabase pooler. Use the direct database host from Supabase for admin session control."
            )

        database_name = settings.DATABASES["default"]["NAME"]
        with psycopg.connect(admin_url) as conn:
            conn.autocommit = True
            if options["list"]:
                self._list_sessions(conn, database_name)
            if options["terminate_all"]:
                self._terminate_sessions(conn, database_name)

    def _list_sessions(self, conn: psycopg.Connection, database_name: str) -> None:
        query = """
            SELECT
                pid,
                usename,
                application_name,
                client_addr::text,
                state,
                backend_start,
                state_change
            FROM pg_stat_activity
            WHERE datname = %s
            ORDER BY backend_start ASC
        """
        with conn.cursor() as cursor:
            cursor.execute(query, [database_name])
            rows = cursor.fetchall()

        if not rows:
            self.stdout.write(self.style.SUCCESS("No active sessions found."))
            return

        self.stdout.write(self.style.WARNING(f"Active sessions for {database_name}: {len(rows)}"))
        for row in rows:
            pid, user_name, app_name, client_addr, state, backend_start, state_change = row
            self.stdout.write(
                f"pid={pid} user={user_name} app={app_name or '-'} client={client_addr or '-'} "
                f"state={state or '-'} started={backend_start} changed={state_change}"
            )

    def _terminate_sessions(self, conn: psycopg.Connection, database_name: str) -> None:
        query = """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s
              AND pid <> pg_backend_pid()
        """
        with conn.cursor() as cursor:
            cursor.execute(query, [database_name])
            results = cursor.fetchall()

        terminated_count = sum(1 for (terminated,) in results if terminated)
        self.stdout.write(
            self.style.SUCCESS(
                f"Terminated {terminated_count} session(s) for database {database_name}."
            )
        )
