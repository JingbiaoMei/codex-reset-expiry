#!/usr/bin/env python3
"""Print Codex reset-credit expiry dates from the local Codex Desktop login."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENDPOINT = "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            value = json.load(fh)
    except FileNotFoundError:
        raise SystemExit(f"Missing Codex auth file: {path}\nOpen Codex Desktop and sign in first.")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")

    if not isinstance(value, dict):
        raise SystemExit(f"Expected {path} to contain a JSON object.")
    return value


def jwt_payload(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None

    parts = token.split(".")
    if len(parts) < 2:
        return None

    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        value = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None

    return value if isinstance(value, dict) else None


def account_id_from_token(token: str | None) -> str | None:
    payload = jwt_payload(token)
    auth = payload.get("https://api.openai.com/auth") if payload else None
    if isinstance(auth, dict):
        account_id = auth.get("chatgpt_account_id")
        if isinstance(account_id, str) and account_id:
            return account_id
    return None


def load_auth_context(codex_home: Path) -> tuple[str, str | None]:
    auth = load_json(codex_home / "auth.json")
    tokens = auth.get("tokens")
    if not isinstance(tokens, dict):
        raise SystemExit(f"Missing 'tokens' object in {codex_home / 'auth.json'}.")

    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise SystemExit(f"Missing access_token in {codex_home / 'auth.json'}.")

    id_token = tokens.get("id_token")
    fallback_account_id = tokens.get("account_id")
    account_id = (
        account_id_from_token(id_token if isinstance(id_token, str) else None)
        or account_id_from_token(access_token)
        or (fallback_account_id if isinstance(fallback_account_id, str) else None)
    )
    return access_token, account_id


def fetch_reset_credits(access_token: str, account_id: str | None, timeout: float) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "originator": "Codex Desktop",
        "OAI-Product-Sku": "CODEX",
        "Accept": "application/json",
    }
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id

    request = urllib.request.Request(ENDPOINT, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from Codex reset-credit endpoint:\n{detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach Codex reset-credit endpoint: {exc.reason}")

    try:
        value = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Codex returned non-JSON response: {exc}")

    if not isinstance(value, dict):
        raise SystemExit("Codex returned JSON, but it was not an object.")
    return value


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()


def format_expiry(value: str | None) -> str:
    parsed = parse_datetime(value)
    if parsed is None:
        return value or "expiry unavailable"

    now = datetime.now(parsed.tzinfo)
    remaining = parsed - now
    if remaining.total_seconds() < 0:
        suffix = "expired"
    else:
        days = remaining.days
        hours = remaining.seconds // 3600
        suffix = f"{days}d {hours}h remaining"
    return f"{parsed:%Y-%m-%d %H:%M:%S %Z} ({suffix})"


def print_reset_credits(data: dict[str, Any], all_statuses: bool) -> None:
    credits = data.get("credits")
    if not isinstance(credits, list):
        credits = []

    available_count = data.get("available_count", data.get("availableCount"))
    print(f"Available reset credits: {available_count if available_count is not None else 'unknown'}")

    shown = 0
    for index, credit in enumerate(credits, start=1):
        if not isinstance(credit, dict):
            continue

        status = str(credit.get("status", "unknown"))
        if not all_statuses and status.lower() != "available":
            continue

        shown += 1
        reset_type = credit.get("reset_type", credit.get("resetType", "unknown"))
        expires_at = credit.get("expires_at", credit.get("expiresAt"))
        print(f"{index}. {reset_type} [{status}] expires: {format_expiry(expires_at)}")

    if shown == 0:
        print("No reset-credit expiry rows found.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("CODEX_HOME", "~/.codex"),
        help="Codex home directory containing auth.json. Defaults to CODEX_HOME or ~/.codex.",
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds.")
    parser.add_argument("--all", action="store_true", help="Show non-available reset credits too.")
    parser.add_argument("--json", action="store_true", help="Print the raw JSON response.")
    args = parser.parse_args()

    codex_home = Path(args.codex_home).expanduser()
    access_token, account_id = load_auth_context(codex_home)
    data = fetch_reset_credits(access_token, account_id, args.timeout)

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print_reset_credits(data, args.all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
