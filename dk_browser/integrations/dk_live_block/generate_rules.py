#!/usr/bin/env python3
"""Adapt DK Live Block's local fallback rules into Chromium MV3 DNR/CSS.

This is a constrained, read-only source adapter, not the complete Firefox
blocking engine. No network access, dependency installer, shell, or JS eval.
Unknown rules fail closed rather than being silently approximated.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

DIR = Path(__file__).resolve().parent
SEED = re.compile(r'const SEED=(\[[\s\S]*?\])\.join\("\\n"\);')
NETWORK = re.compile(r'^\|\|([a-z0-9.-]+)\^(?:\$media,domain=([a-z0-9.-]+))?$')
COSMETIC = re.compile(r'^(?:(youtube\.com))?##([a-z0-9.#_-]+)$')


def generate(source: str) -> dict[str, str]:
    match = SEED.search(source)
    if not match:
        raise ValueError("DK Live Block fallback SEED not found")
    entries = json.loads(match.group(1))
    if not isinstance(entries, list) or not all(isinstance(x, str) for x in entries):
        raise ValueError("Invalid DK Live Block fallback rules")
    network_rules, generic, youtube = [], [], []
    for line in entries:
        if line.startswith("!") or not line:
            continue
        parsed_network = NETWORK.fullmatch(line)
        if parsed_network:
            host, initiator = parsed_network.groups()
            condition = {"urlFilter": "||" + host + "^"}
            if initiator:
                condition.update(resourceTypes=["media"], initiatorDomains=[initiator])
            network_rules.append({
                "id": len(network_rules) + 1,
                "priority": 1,
                "action": {"type": "block"},
                "condition": condition,
            })
            continue
        parsed_cosmetic = COSMETIC.fullmatch(line)
        if parsed_cosmetic:
            (youtube if parsed_cosmetic.group(1) else generic).append(
                parsed_cosmetic.group(2))
            continue
        raise ValueError("Unsupported DK Live Block filter: " + line)
    if not network_rules:
        raise ValueError("No valid network rules")
    return {
        "rules.json": json.dumps(network_rules, ensure_ascii=False, indent=2) + "\n",
        "cosmetics.css": (
            "/* DK Live Block: initial built-in global cosmetics from src/background.js SEED. */\n"
            + ",\n".join(generic) + " { display:none !important; }\n"
        ),
        "youtube.css": (
            "/* DK Live Block: initial YouTube cosmetics from src/background.js SEED. */\n"
            + ",\n".join(youtube) + " { display:none !important; }\n"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Path to existing dkliveblock/src/background.js")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true",
                       help="Verify checked-in DNR/CSS matches source")
    modes.add_argument("--write", action="store_true",
                       help="Refresh only checked-in DNR/CSS source assets")
    opts = parser.parse_args(argv)
    try:
        result = generate(opts.source.read_text(encoding="utf-8"))
        for name, expected in result.items():
            destination = DIR / name
            if opts.check:
                if destination.read_text(encoding="utf-8") != expected:
                    raise ValueError(name + " differs from DK Live Block's fallback SEED")
            else:
                destination.write_text(expected, encoding="utf-8")
        print("DK Live Block rules match source" if opts.check
              else "DK Live Block rules refreshed")
        return 0
    except (OSError, ValueError) as exc:
        print("DK Live Block integration: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
