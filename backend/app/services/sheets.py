"""Google Sheets integration — reads live data from the EBL spreadsheet.

Sheet layout expected:
  "Недельный зачет":
      row 0  – column totals (ignored)
      row 1  – headers: [blank], "Всего", "W9", "W8", ..., "W1"
      row 2+ – data: [name, total_visits, w9_visits, w8_visits, ...]

  "Все бани":
      row 0  – headers: "страна", "город", "название", <user1>, <user2>, ...
      row 1+ – data: [country, city, bath_name, u1_visits, u2_visits, ...]

  "Общий зачет":
      row 0  – headers: [blank], "Итого", "К-во", ..., "W8", "W7", ..., "W1"
      row 1+ – data: [name, total_pts, visit_count, ..., w8_pts, w7_pts, ...]
"""

import asyncio
import json
import os
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


# ---------------------------------------------------------------------------
# Sync helpers (run in thread pool via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _sync_weekly_stats(credentials_file: str, spreadsheet_id: str, week_num: int) -> list[dict]:
    """Return per-person visit counts for *week_num* from 'Недельный зачет'."""
    client = _make_client(credentials_file)
    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet("Недельный зачет")
    except gspread.WorksheetNotFound:
        titles = [w.title for w in sh.worksheets()]
        raise ValueError(f"Лист 'Недельный зачет' не найден. Доступные листы: {titles}")
    data = ws.get_all_values()

    # Find the header row (contains "Всего")
    header_row_idx = next(
        (i for i, row in enumerate(data) if "Всего" in row), None
    )
    if header_row_idx is None:
        return []

    header = data[header_row_idx]
    week_key = f"W{week_num}"
    week_col = next((i for i, h in enumerate(header) if h.strip() == week_key), None)
    total_col = next((i for i, h in enumerate(header) if h.strip() == "Всего"), None)

    if week_col is None:
        return []

    results = []
    for row in data[header_row_idx + 1:]:
        name = row[0].strip() if row else ""
        if not name:
            continue
        raw = row[week_col].strip() if week_col < len(row) else ""
        try:
            count = int(raw)
        except ValueError:
            count = 0
        if count <= 0:
            continue
        total_raw = row[total_col].strip() if total_col and total_col < len(row) else ""
        try:
            total = int(total_raw)
        except ValueError:
            total = 0
        results.append({"name": name, "visit_count": count, "total_visits": total})

    return sorted(results, key=lambda x: -x["visit_count"])


def _sync_overall_stats(credentials_file: str, spreadsheet_id: str) -> list[dict]:
    """Return overall standings from 'Общий зачет' (total points + visit count)."""
    client = _make_client(credentials_file)
    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet("Общий зачет")
    except gspread.WorksheetNotFound:
        titles = [w.title for w in sh.worksheets()]
        raise ValueError(f"Лист 'Общий зачет' не найден. Доступные листы: {titles}")
    data = ws.get_all_values()

    if not data:
        return []

    header = data[0]
    itogo_col = next((i for i, h in enumerate(header) if h.strip() == "Итого"), None)
    kvo_col = next((i for i, h in enumerate(header) if h.strip() == "К-во"), None)

    results = []
    for row in data[1:]:
        name = row[0].strip() if row else ""
        if not name:
            continue
        pts_raw = row[itogo_col].replace(",", ".").strip() if itogo_col and itogo_col < len(row) else ""
        kvo_raw = row[kvo_col].strip() if kvo_col and kvo_col < len(row) else ""
        try:
            pts = float(pts_raw)
        except ValueError:
            pts = 0.0
        try:
            kvo = int(kvo_raw)
        except ValueError:
            kvo = 0
        if pts > 0 or kvo > 0:
            results.append({"name": name, "points": pts, "visit_count": kvo})

    return sorted(results, key=lambda x: -x["points"])


def _sync_bath_map(credentials_file: str, spreadsheet_id: str) -> list[dict]:
    """Return per-bath per-user visit counts from 'Все бани'."""
    client = _make_client(credentials_file)
    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet("Все бани")
    except gspread.WorksheetNotFound:
        titles = [w.title for w in sh.worksheets()]
        raise ValueError(f"Лист 'Все бани' не найден. Доступные листы: {titles}")
    data = ws.get_all_values()

    if not data:
        return []

    header = data[0]
    # Columns: 0=country, 1=city, 2=name, 3+=users
    user_names = [h.strip() for h in header[3:] if h.strip()]

    baths = []
    for row in data[1:]:
        if len(row) < 3 or not row[2].strip():
            continue
        country = row[0].strip()
        city = row[1].strip()
        bath_name = row[2].strip()

        visitors = []
        total = 0
        for i, user_name in enumerate(user_names):
            col_idx = i + 3
            raw = row[col_idx].strip() if col_idx < len(row) else ""
            try:
                count = int(raw)
            except ValueError:
                count = 0
            if count > 0:
                visitors.append({"name": user_name, "visit_count": count})
                total += count

        if total > 0:
            baths.append({
                "bath_name": bath_name,
                "city": city,
                "country": country,
                "total_visits": total,
                "visitors": sorted(visitors, key=lambda x: -x["visit_count"]),
            })

    return sorted(baths, key=lambda x: -x["total_visits"])


# ---------------------------------------------------------------------------
# Async public API
# ---------------------------------------------------------------------------

async def get_weekly_stats(credentials_file: str, spreadsheet_id: str, week_num: int) -> list[dict]:
    return await asyncio.to_thread(_sync_weekly_stats, credentials_file, spreadsheet_id, week_num)


async def get_overall_stats(credentials_file: str, spreadsheet_id: str) -> list[dict]:
    return await asyncio.to_thread(_sync_overall_stats, credentials_file, spreadsheet_id)


async def get_bath_map(credentials_file: str, spreadsheet_id: str) -> list[dict]:
    return await asyncio.to_thread(_sync_bath_map, credentials_file, spreadsheet_id)
