"""Fail closed on unsafe Docker runtime settings. Never print secret values.

This guards the image's normal entrypoint; it is not a legal/payment approval
or a substitute for Django deployment checks and an external security review.
"""
from __future__ import annotations

import os
import ipaddress
import re
import sys
from collections.abc import Mapping
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    """A configuration problem with a deliberately redacted message."""


def valid_hostname(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return bool(len(value) <= 253 and '.' in value and all(
            re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part)
            for part in value.split('.')))
    return False


def validate(env: Mapping[str, str]) -> list[str]:
    problems: list[str] = []
    for name in ("DEBUG", "TESTING"):
        if env.get(name, "0") != "0":
            problems.append(f"{name} must be 0 in the deployed image.")
    secret = env.get("DJANGO_SECRET_KEY", "")
    if (len(secret) < 50 or len(set(secret)) < 5
            or any(marker in secret.lower() for marker in
                   ("local-development", "change_me", "change-me", "changeme", "django-insecure-"))):
        problems.append("DJANGO_SECRET_KEY must be a private generated key, not an example.")

    host = None
    try:
        raw_site = env.get("SITE_URL", "")
        site = urlsplit(raw_site)
        host = site.hostname
        valid_site = (raw_site == raw_site.strip() and not any(ord(c) < 32 for c in raw_site)
                      and site.scheme == "https" and host and site.port in (None, 443)
                      and not site.username and not site.password
                      and site.path in ("", "/") and not site.query and not site.fragment
                      and valid_hostname(host)
                      and "." in host and not host.endswith((".invalid", ".localhost", ".test"))
                      and host not in ("localhost", "127.0.0.1", "0.0.0.0"))
    except ValueError:
        valid_site = False
    if not valid_site:
        problems.append("SITE_URL must be a complete HTTPS origin on the configured domain.")
    hosts = [value.strip().lower() for value in env.get("ALLOWED_HOSTS", "").split(",") if value.strip()]
    if (not hosts or host not in hosts
            or any(not valid_hostname(value) for value in hosts)):
        problems.append("ALLOWED_HOSTS must list exact hostnames and include SITE_URL's host.")
    if env.get("TRUST_PROXY", "0") != "1":
        problems.append("TRUST_PROXY must be 1 behind the bundled private Caddy proxy.")

    try:
        db = urlsplit(env.get("DATABASE_URL", ""))
        valid_db = (db.scheme in ("postgres", "postgresql") and db.hostname
                    and db.username and db.password and db.path not in ("", "/")
                    and db.port != 0 and not db.fragment)
        if valid_db and any(marker in (db.password or "").lower() for marker in
                            ("change_me", "change-me", "changeme")):
            valid_db = False
    except ValueError:
        valid_db = False
    if not valid_db:
        problems.append("DATABASE_URL must identify PostgreSQL with private credentials and a database.")
    if env.get("MEDIA_ROOT", "") != "/data/media":
        problems.append("MEDIA_ROOT must match the bundled persistent volume: /data/media.")

    registration = env.get("REGISTRATION_OPEN", "0")
    if registration not in ("0", "1"):
        problems.append("REGISTRATION_OPEN must be 0 or 1.")
    mode = env.get("PAYMENTS_MODE", "disabled")
    if mode not in ("disabled", "test", "live"):
        problems.append("PAYMENTS_MODE must be disabled, test, or live.")
    if mode in ("test", "live"):
        if not env.get("STRIPE_SECRET_KEY", "").startswith(f"sk_{mode}_"):
            problems.append("STRIPE_SECRET_KEY must match the selected payment mode.")
        hooks = [env.get(name, "") for name in ("STRIPE_WEBHOOK_SECRET", "STRIPE_CONNECT_WEBHOOK_SECRET")]
        if any(not key.startswith("whsec_") or len(key) <= 6 for key in hooks) or hooks[0] == hooks[1]:
            problems.append("Configure two different signed webhook secrets for platform and Connect.")
    if mode == "live":
        for name in ("PROVIDER_APPROVED", "PRIVATE_SELLERS_APPROVED", "LIVE_APPROVED"):
            if env.get(name) != "1":
                problems.append(f"{name} must be recorded before live operation.")
    if registration == "1" or mode == "live":
        if (env.get("EMAIL_BACKEND") != "django.core.mail.backends.smtp.EmailBackend"
                or not env.get("EMAIL_HOST") or env.get("EMAIL_USE_TLS") != "1"):
            problems.append("Public registration/live operation requires configured TLS SMTP.")
        for name in ("DEFAULT_FROM_EMAIL", "SUPPORT_EMAIL"):
            address = env.get(name, "")
            if (not re.fullmatch(r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+", address)
                    or address.endswith((".invalid", ".localhost"))):
                problems.append(f"{name} must be a configured email address.")
    try:
        days = int(env.get("PAYOUT_HOLD_DAYS", "7"))
        if not 0 <= days <= 365:
            raise ValueError
    except ValueError:
        problems.append("PAYOUT_HOLD_DAYS must be an integer from 0 to 365.")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    problems = validate(os.environ)
    if problems:
        print("Deployment blocked:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 2
    if argv == ["--check"]:
        print("Runtime configuration checks passed; this does not certify live-commerce readiness.")
        return 0
    if not argv:
        print("No service command supplied.", file=sys.stderr)
        return 2
    try:
        os.execvp(argv[0], argv)
    except OSError:
        print("Service command could not be started.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
