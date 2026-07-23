#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


TARGET_SERVER_NAMES = ("mindmetric.store", "www.mindmetric.store")

GZIP_BLOCK = """    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 5;
    gzip_types
        text/plain
        text/css
        text/javascript
        application/javascript
        application/json
        application/xml
        image/svg+xml;
"""

STATIC_BLOCK = """    location /static/ {
        alias /home/ec2-user/ThomasGia/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
        access_log off;
    }
"""


def iter_server_blocks(text: str):
    blocks: list[tuple[int, int, str]] = []
    idx = 0
    while True:
        start = text.find("server {", idx)
        if start == -1:
            break
        depth = 0
        end = None
        for pos in range(start, len(text)):
            char = text[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = pos + 1
                    break
        if end is None:
            raise ValueError("Unbalanced braces in nginx config.")
        blocks.append((start, end, text[start:end]))
        idx = end
    return blocks


def should_patch(block: str) -> bool:
    return "server_name" in block and any(name in block for name in TARGET_SERVER_NAMES)


def ensure_gzip(block: str) -> str:
    if "gzip on;" in block:
        return block
    return re.sub(r"(server_name\s+[^\n]+;\n)", r"\1\n" + GZIP_BLOCK + "\n", block, count=1)


def ensure_static_block(block: str) -> str:
    static_pattern = re.compile(r"(?ms)^    location /static/ \{\n.*?^    \}\n?")
    if static_pattern.search(block):
        return static_pattern.sub(STATIC_BLOCK + "\n", block, count=1)

    location_root = "    location / {\n"
    if location_root in block:
        return block.replace(location_root, STATIC_BLOCK + "\n" + location_root, 1)

    return block[:-2] + "\n" + STATIC_BLOCK + "}\n"


def patch_config(text: str) -> str:
    blocks = iter_server_blocks(text)
    if not blocks:
        raise ValueError("No server blocks found in nginx config.")

    updated = []
    cursor = 0
    for start, end, block in blocks:
        updated.append(text[cursor:start])
        if should_patch(block):
            block = ensure_gzip(block)
            block = ensure_static_block(block)
        updated.append(block)
        cursor = end
    updated.append(text[cursor:])
    return "".join(updated)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: sync_nginx_conf.py /etc/nginx/conf.d/mindmetric.conf", file=sys.stderr)
        return 2

    config_path = Path(sys.argv[1])
    original = config_path.read_text()
    patched = patch_config(original)
    if patched != original:
        config_path.write_text(patched)
        print(f"Updated nginx config: {config_path}")
    else:
        print(f"Nginx config already up to date: {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
