#!/usr/bin/env python3
"""
Print the SHA-256 and size of the FULL response body of a URL.

register_claim and challenge need this commitment. The contract hashes the raw response
bytes, so this script hashes raw bytes too (no decoding, no newline changes).

    python scripts/hash_url.py https://raw.githubusercontent.com/<user>/<repo>/main/docs/limits.md
"""
import hashlib
import sys
import urllib.request


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    url = sys.argv[1]
    req = urllib.request.Request(url, headers={"User-Agent": "docs-claim-ledger-hash"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        print("status :", resp.status)
    print("bytes  :", len(body))
    print("sha256 :", hashlib.sha256(body).hexdigest())
    if len(body) > 64 * 1024:
        print("WARNING: body is over 64 KiB; the contract cannot settle this page (INCONCLUSIVE)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
