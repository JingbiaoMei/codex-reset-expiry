# codex-reset-expiry

Small Python CLI for checking Codex reset-credit expiry dates.

It uses the same ChatGPT backend endpoint as
[`jordan-edai/codex-reset-watcher`](https://github.com/jordan-edai/codex-reset-watcher)
and reads the bearer token from your local Codex auth file.

## Usage

Run from the repository root:

```bash
python3 check_codex_reset_expiry.py
```

Useful options:

```bash
python3 check_codex_reset_expiry.py --all
python3 check_codex_reset_expiry.py --json
python3 check_codex_reset_expiry.py --codex-home ~/.codex
```

## Auth

The script reads `~/.codex/auth.json` by default, or `$CODEX_HOME/auth.json`
when `CODEX_HOME` is set.

Do not copy `auth.json`, API keys, tokens, or local credential folders into this
repository.

## Notes

- No third-party Python dependencies are required.
- The script does not print your bearer token.
- Network access to `chatgpt.com` is required.
