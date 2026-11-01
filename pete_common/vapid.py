"""`pete-vapid` — generate VAPID keys into data/vapid.json.

    venv/bin/pete-vapid              # writes ./data/vapid.json
    venv/bin/pete-vapid path/to.json
    venv/bin/pete-vapid --force      # overwrite existing keys (breaks
                                     # every existing push subscription)

Needs py_vapid, which pywebpush pulls in.
"""

import argparse
import base64
import json
import sys
from pathlib import Path


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate() -> dict:
    from py_vapid import Vapid

    vapid = Vapid()
    vapid.generate_keys()
    priv = vapid.private_key.private_numbers().private_value
    pub = vapid.public_key.public_numbers()
    return {
        "private_base64url": _b64url(priv.to_bytes(32, "big")),
        "public_base64url": _b64url(b"\x04" + pub.x.to_bytes(32, "big") + pub.y.to_bytes(32, "big")),
        "private_pem": vapid.private_pem().decode(),
        "public_pem": vapid.public_pem().decode(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pete-vapid", description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", default="data/vapid.json")
    parser.add_argument("--force", action="store_true", help="overwrite existing keys")
    args = parser.parse_args(argv)

    path = Path(args.path)
    if path.exists() and not args.force:
        print(f"{path} already exists — pass --force to overwrite "
              "(invalidates all existing subscriptions)", file=sys.stderr)
        return 1
    from pete_common.jsonio import write_json

    path.parent.mkdir(parents=True, exist_ok=True)
    data = generate()
    write_json(path, data)
    path.chmod(0o600)
    print(f"wrote {path}\npublic key (base64url):\n{data['public_base64url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
