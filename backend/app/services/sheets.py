"""Google Sheets integration — reads live data from the EBL spreadsheet.

Actual sheet layout (confirmed from file):
  "недельный зачет":
      row 0  – column totals (ignored)
      row 1  – headers: [blank], "Всего", "W9", "W8", ..., "W1"
      row 2+ – data: [name, total_visits, w9_visits, w8_visits, ...]

  "все бани":
      row 0  – headers: "Страна", "Регион", <total>, <user1>, <user2>, ...
      rows 1-6 – category summaries (country is empty — skip)
      row 7+  – data: [country, region, bath_name, u1_visits, u2_visits, ...]

  "Общий зачет":
      row 0  – headers: [blank/0], "Итого", "К-во", ..., "W8", "W7", ..., "W1"
      row 1+ – data: [name, total_pts, visit_count, ..., w8_pts, w7_pts, ...]
"""

import asyncio
import json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _make_client(credentials: str) -> gspread.Client:
    """Accept either a JSON string (from env var) or a file path."""
    if credentials.strip().startswith("{"):
        info = json.loads(credentials)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(credentials, scopes=SCOPES)
    return gspread.authorize(creds)


def _to_int(raw) -> int:
    """Convert a cell value (string or number) to int, return 0 on failure."""
    if raw is None:
        return 0
    s = str(raw).strip().replace(",", ".").replace("\xa0", "")
    if not s:
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _to_float(raw) -> float:
    """Convert a cell value to float, return 0.0 on failure."""
    if raw is None:
        return 0.0
    s = str(raw).strip().replace(",", ".").replace("\xa0", "")
    if not s:
        return 0.0
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _str(raw) -> str:
    """Convert a cell to stripped string, empty string on None."""
    if raw is None:
        return ""
    return str(raw).strip()


def _open_sheet(sh, name: str):
    try:
        return sh.worksheet(name)
    except gspread.WorksheetNotFound:
        titles = [w.title for w in sh.worksheets()]
        raise ValueError(f"Лист '{name}' не найден. Доступные листы: {titles}")


# ---------------------------------------------------------------------------
# Sync helpers (run in thread pool via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _sync_weekly_stats(credentials: str, spreadsheet_id: str, week_num: int) -> list[dict]:
    """Return per-person visit counts for *week_num* from 'недельный зачет'."""
    sh = _make_client(credentials).open_by_key(spreadsheet_id)
    ws = _open_sheet(sh, "недельный зачет")
    data = ws.get_all_values()

    # Find the header row (contains "Всего")
    header_row_idx = next(
        (i for i, row in enumerate(data) if "Всего" in row), None
    )
    if header_row_idx is None:
        return []

    header = data[header_row_idx]
    week_key = f"W{week_num}"
    week_col = next((i for i, h in enumerate(header) if _str(h) == week_key), None)
    total_col = next((i for i, h in enumerate(header) if _str(h) == "Всего"), None)

    if week_col is None:
        return []

    results = []
    for row in data[header_row_idx + 1:]:
        name = _str(row[0]) if row else ""
        if not name:
            continue
        count = _to_int(row[week_col] if week_col < len(row) else "")
        if count <= 0:
            continue
        total = _to_int(row[total_col] if total_col is not None and total_col < len(row) else "")
        results.append({"name": name, "visit_count": count, "total_visits": total})

    return sorted(results, key=lambda x: -x["visit_count"])


def _sync_overall_stats(credentials: str, spreadsheet_id: str) -> list[dict]:
    """Return overall standings from 'Общий зачет'."""
    sh = _make_client(credentials).open_by_key(spreadsheet_id)
    ws = _open_sheet(sh, "Общий зачет")
    data = ws.get_all_values()

    if not data:
        return []

    header = data[0]
    itogo_col = next((i for i, h in enumerate(header) if _str(h) == "Итого"), None)
    kvo_col = next((i for i, h in enumerate(header) if _str(h) == "К-во"), None)

    results = []
    for row in data[1:]:
        name = _str(row[0]) if row else ""
        if not name:
            continue
        pts = _to_float(row[itogo_col] if itogo_col is not None and itogo_col < len(row) else "")
        kvo = _to_int(row[kvo_col] if kvo_col is not None and kvo_col < len(row) else "")
        if pts > 0 or kvo > 0:
            results.append({"name": name, "points": pts, "visit_count": kvo})

    return sorted(results, key=lambda x: -x["points"])


def _sync_bath_map(credentials: str, spreadsheet_id: str) -> list[dict]:
    """Return per-bath per-user visit counts from 'все бани'.

    Layout: row 0 = headers [Страна, Регион, <total>, user1, user2, ...]
            rows 1-6 = category summaries (country column is empty — skip)
            row 7+   = actual baths [country, region, bath_name, counts...]
    """
    sh = _make_client(credentials).open_by_key(spreadsheet_id)
    ws = _open_sheet(sh, "все бани")
    data = ws.get_all_values()

    if not data:
        return []

    header = data[0]
    # User names start at column 3 (after Страна, Регион, total)
    user_names = [_str(h) for h in header[3:] if _str(h)]

    baths = []
    for row in data[1:]:
        # Skip category summary rows (country column is empty)
        if len(row) < 3 or not _str(row[0]) or not _str(row[2]):
            continue

        country = _str(row[0])
        region = _str(row[1])
        bath_name = _str(row[2])

        visitors = []
        total = 0
        for i, user_name in enumerate(user_names):
            col_idx = i + 3
            count = _to_int(row[col_idx] if col_idx < len(row) else "")
            if count > 0:
                visitors.append({"name": user_name, "visit_count": count})
                total += count

        if total > 0:
            baths.append({
                "bath_name": bath_name,
                "region": region,
                "country": country,
                "total_visits": total,
                "visitors": sorted(visitors, key=lambda x: -x["visit_count"]),
            })

    return sorted(baths, key=lambda x: -x["total_visits"])


# ---------------------------------------------------------------------------
# Async public API
# ---------------------------------------------------------------------------

async def get_weekly_stats(credentials: str, spreadsheet_id: str, week_num: int) -> list[dict]:
    return await asyncio.to_thread(_sync_weekly_stats, credentials, spreadsheet_id, week_num)


async def get_overall_stats(credentials: str, spreadsheet_id: str) -> list[dict]:
    return await asyncio.to_thread(_sync_overall_stats, credentials, spreadsheet_id)


async def get_bath_map(credentials: str, spreadsheet_id: str) -> list[dict]:
    return await asyncio.to_thread(_sync_bath_map, credentials, spreadsheet_id)
