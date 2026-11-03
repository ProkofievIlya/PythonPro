"""Компілює locale/*/LC_MESSAGES/*.po у .mo без GNU gettext (msgfmt).

Корисно на Windows, де ``python manage.py compilemessages`` потребує встановлених
gettext-утиліт. Підтримує msgctxt, множину (msgid_plural / msgstr[N]) і пропускає
fuzzy-записи.

Запуск з кореня проєкту:

    python scripts/compile_messages.py
"""

from __future__ import annotations

import ast
import struct
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = BASE_DIR / "locale"


def _unquote(token: str) -> str:
    return ast.literal_eval(token)


def parse_po(text: str) -> dict[bytes, bytes]:
    """Повертає {ключ .mo: переклад} у форматі, який читає gettext."""
    messages: dict[bytes, bytes] = {}
    entry: dict[str, object] = {}
    field: str | None = None
    fuzzy = False

    def flush() -> None:
        nonlocal entry, field, fuzzy
        if "msgid" in entry and not (fuzzy and entry["msgid"] != ""):
            msgid = str(entry["msgid"])
            ctxt = entry.get("msgctxt")
            plural = entry.get("msgid_plural")
            strs: dict[int, str] = entry.get("msgstr", {})  # type: ignore[assignment]
            translation = "\0".join(strs[i] for i in sorted(strs))
            if translation or msgid == "":
                key = msgid
                if plural is not None:
                    key = f"{msgid}\0{plural}"
                if ctxt is not None:
                    key = f"{ctxt}\x04{key}"
                messages[key.encode("utf-8")] = translation.encode("utf-8")
        entry = {}
        field = None
        fuzzy = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("#"):
            if line.startswith("#,") and "fuzzy" in line:
                fuzzy = True
            continue
        if line.startswith('"'):
            value = _unquote(line)
            if field is None:
                continue
            if field.startswith("msgstr"):
                index = int(field[7:-1]) if "[" in field else 0
                strs = entry.setdefault("msgstr", {})  # type: ignore[assignment]
                strs[index] += value  # type: ignore[index]
            else:
                entry[field] = str(entry.get(field, "")) + value
            continue
        keyword, _, rest = line.partition(" ")
        if keyword == "msgctxt" and "msgid" in entry:
            flush()
        if keyword == "msgid" and "msgid" in entry:
            flush()
        field = keyword
        value = _unquote(rest.strip())
        if keyword.startswith("msgstr"):
            index = int(keyword[7:-1]) if "[" in keyword else 0
            strs = entry.setdefault("msgstr", {})  # type: ignore[assignment]
            strs[index] = value  # type: ignore[index]
        else:
            entry[keyword] = value
    flush()
    return messages


def build_mo(messages: dict[bytes, bytes]) -> bytes:
    keys = sorted(messages)
    ids = b""
    strs = b""
    offsets = []
    for key in keys:
        offsets.append((len(ids), len(key), len(strs), len(messages[key])))
        ids += key + b"\0"
        strs += messages[key] + b"\0"
    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)
    koffsets: list[int] = []
    voffsets: list[int] = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    table = koffsets + voffsets
    header = struct.pack(
        "Iiiiiii", 0x950412DE, 0, len(keys), 7 * 4, 7 * 4 + len(keys) * 8, 0, 0
    )
    return header + struct.pack(f"{len(table)}i", *table) + ids + strs


def compile_all(locale_dir: Path = LOCALE_DIR) -> list[Path]:
    written: list[Path] = []
    for po_path in sorted(locale_dir.glob("*/LC_MESSAGES/*.po")):
        messages = parse_po(po_path.read_text(encoding="utf-8"))
        mo_path = po_path.with_suffix(".mo")
        mo_path.write_bytes(build_mo(messages))
        written.append(mo_path)
        print(f"{po_path.relative_to(BASE_DIR)} -> {mo_path.name} ({len(messages)} записів)")
    return written


if __name__ == "__main__":
    if not compile_all():
        sys.exit("Не знайдено жодного .po файла")
