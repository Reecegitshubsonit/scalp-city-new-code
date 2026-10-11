#!/usr/bin/env python3
"""Sort a pasted list of keys (keys.txt) into .env. Prints names only, never values.

Accepts lines like `NAME=value`, `NAME: value`, or `Label value`.
Usage: python3 setup_env.py [keys.txt]
"""
import os
import re
import sys

TARGETS = {
    "WEBULL_APP_KEY": ["webullappkey", "webullkey", "webullapikey", "webullclientid"],
    "WEBULL_APP_SECRET": ["webullappsecret", "webullsecret", "webullapisecret"],
    "WEBULL_ACCOUNT_ID": ["webullaccountid", "webullaccount", "webullaccountnumber"],
    "ALPACA_API_KEY": ["alpacaapikey", "alpacakey", "alpacakeyid", "alpacaapikeyid"],
    "ALPACA_SECRET_KEY": ["alpacasecretkey", "alpacasecret", "alpacaapisecret"],
    "WEBULL_PAPER_ACCOUNT_NUMBER": ["webullpaperaccountnumber", "webullpaperaccount"],
    "WEBULL_PAPER_ACCOUNT_CLASS": ["webullpaperaccountclass"],
    "WEBULL_SANDBOX_ACCOUNT_ATTESTED": ["webullsandboxaccountattested", "webullsandboxattested"],
    "ALPACA_DATA_FEED": ["alpacadatafeed", "alpacafeed"],
    "DATA_PROVIDER": ["dataprovider"],
    "MASSIVE_API_KEY": ["massiveapikey", "massivekey", "polygonapikey", "polygonkey"],
    "DATABENTO_API_KEY": ["databentoapikey", "databentokey"],
    "FMP_API_KEY": ["fmpapikey", "fmpkey"],
    "SEC_USER_AGENT": ["secuseragent"],
}
LOOKUP = {alias: name for name, aliases in TARGETS.items() for alias in aliases}
LOOKUP.update({name.replace("_", "").lower(): name for name in TARGETS})


def norm(label):
    return re.sub(r"[^a-z0-9]", "", label.lower())


def parse(path):
    found = {}
    with open(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^(.*?)\s*[=:]\s*(.+)$", line) or re.match(r"^(.*\D)\s+(\S+)$", line)
            if not match:
                continue
            name = LOOKUP.get(norm(match.group(1)))
            value = match.group(2).strip().strip("\"'")
            if name and value:
                found[name] = value
    return found


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "keys.txt"
    if not os.path.exists(src):
        sys.exit(f"{src} not found")
    if os.path.exists(".env"):
        sys.exit(".env already exists; move it aside first (nothing changed)")
    found = parse(src)
    lines = ["# PAPER / SANDBOX ONLY", "WEBULL_ENV=sandbox"]
    lines += [f"{name}={found.get(name, '')}" for name in TARGETS]
    fd = os.open(".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    for name in TARGETS:
        print(f"{name:20s} {'set' if name in found else 'MISSING'}")
    size = os.path.getsize(src)
    with open(src, "r+b") as handle:  # overwrite before delete
        handle.write(b"0" * size)
    os.remove(src)
    print("keys.txt wiped. .env written (mode 600).")


if __name__ == "__main__":
    main()
