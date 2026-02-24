import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedMessage:
    bath_name: str | None = None
    mentioned_usernames: list[str] = field(default_factory=list)
    mentioned_user_ids: list[int] = field(default_factory=list)
    flag_long: bool = False
    flag_ultraunique: bool = False
    visited_at: datetime | None = None


LONG_KEYWORDS = [
    r"долго",
    r"150\+",
    r">\s*150",
    r"\d{3,}\s*мин",
    r"3\s*час",
    r"4\s*час",
    r"5\s*час",
    r"long",
    r"длительно",
]

ULTRA_KEYWORDS = [
    r"ультрауникально",
    r"ультра\s*уникально",
    r"ультра-уникально",
    r"\bультра\b",
]


def parse_message(text: str, bot_username: str | None = None) -> ParsedMessage:
    result = ParsedMessage()

    # Remove bot mention
    if bot_username:
        text = re.sub(rf"@{re.escape(bot_username)}", "", text, flags=re.IGNORECASE)

    # Extract @usernames
    result.mentioned_usernames = re.findall(r"@(\w+)", text)

    # Extract tg user IDs
    result.mentioned_user_ids = [
        int(i) for i in re.findall(r"tg://user\?id=(\d+)", text)
    ]

    # Clean text for bath name parsing
    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"tg://user\?id=\d+", "", clean).strip()

    text_lower = text.lower()

    # Detect flags
    for kw in LONG_KEYWORDS:
        if re.search(kw, text_lower):
            result.flag_long = True
            break

    for kw in ULTRA_KEYWORDS:
        if re.search(kw, text_lower):
            result.flag_ultraunique = True
            break

    # Extract bath name — priority order:
    # 1. Explicit "баня: X" or "сауна: X"
    m = re.search(r"(?:баня|сауна|баню|бане)[:\s]+([^\n,]{2,80})", clean, re.IGNORECASE)
    if m:
        result.bath_name = m.group(1).strip().rstrip(".,!?")
        return result

    # 2. "были в X" / "посетили X" / "сходили в X"
    m = re.search(
        r"(?:были\s+в|посетили|сходили\s+в|побывали\s+в|заглянули\s+в)\s+([^\n,]{2,80})",
        clean, re.IGNORECASE
    )
    if m:
        result.bath_name = m.group(1).strip().rstrip(".,!?")
        return result

    # 3. First meaningful phrase (first line, first comma-chunk)
    first_line = clean.split("\n")[0].strip()
    # Remove known flag words
    for kw in ["долго", "ультра", "150+", "long"]:
        first_line = re.sub(kw, "", first_line, flags=re.IGNORECASE).strip()
    first_phrase = re.split(r"[,;]", first_line)[0].strip().rstrip(".,!?")
    if len(first_phrase) >= 2:
        result.bath_name = first_phrase

    return result
