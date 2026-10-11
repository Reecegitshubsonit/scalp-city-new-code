#!/usr/bin/env python3
"""Set one variable in .env without echoing the value.

Usage: python3 set_key.py MASSIVE_API_KEY
"""
import getpass
import os
import re
import sys

if len(sys.argv) != 2 or not re.fullmatch(r"[A-Z][A-Z0-9_]*", sys.argv[1]):
    sys.exit("usage: python3 set_key.py NAME   (e.g. MASSIVE_API_KEY)")
name = sys.argv[1]
if not os.path.exists(".env"):
    sys.exit(".env not found; run this from ~/scalp-city")
value = getpass.getpass(f"{name} (hidden): ").strip()
if not value:
    sys.exit("empty value; nothing changed")
text = open(".env").read()
line = f"{name}={value}"
if re.search(rf"^{name}=.*$", text, flags=re.M):
    text = re.sub(rf"^{name}=.*$", lambda _: line, text, flags=re.M)
else:
    text += ("" if text.endswith("\n") else "\n") + line + "\n"
with open(".env", "w") as handle:
    handle.write(text)
os.chmod(".env", 0o600)
print(f"{name} set.")
