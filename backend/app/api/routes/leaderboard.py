import os

from fastapi import APIRouter, Depends, HTTPException

from app.db.models import User
from app.api.deps import get_current_user
from app.services import sheets as sheets_svc
from app.config import settings

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def _creds_file() -> str:
    here = os.path.dirname(__file__)  # backend/app/api/routes/
    return os.path.join(here, "..", "..", "..", "google_credentials.json")


@router.get("")
async def get_leaderboard(
    current_user: User = Depends(get_current_user),
):
    """Overall standings from Google Sheets 'Общий зачет'."""
    try:
        rows = await sheets_svc.get_overall_stats(
            _creds_file(), settings.GOOGLE_SPREADSHEET_ID
        )
    except Exception as e:
        raise HTTPException(500, f"Sheets error: {e}")

    return [
        {
            "rank": i + 1,
            "name": row["name"],
            "points": row["points"],
            "visit_count": row["visit_count"],
        }
        for i, row in enumerate(rows)
    ]
