from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from rapidfuzz import fuzz
from app.db.models.bath import Bath, Country, Region


def normalize(s: str) -> str:
    s = s.lower().strip()
    for word in ["баня", "сауна", "banya", "sauna", "бани", "сауны", "банный", "комплекс"]:
        s = s.replace(word, "")
    return " ".join(s.split())


async def search_baths(db: AsyncSession, query: str, limit: int = 5) -> list[tuple]:
    """Return list of (Bath, score) sorted by score desc."""
    q = normalize(query)
    result = await db.execute(
        select(Bath).where(Bath.is_archived == False, Bath.canonical_id.is_(None))
    )
    baths = result.scalars().all()
    if not baths:
        return []

    candidates = []
    for bath in baths:
        names = [bath.name] + (bath.aliases or [])
        best = max(fuzz.token_sort_ratio(q, normalize(n)) for n in names)
        candidates.append((bath, best))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:limit]


async def find_best_bath(db: AsyncSession, query: str) -> tuple:
    """
    Returns:
        (bath, []) if confident match (score >= 80)
        (None, top5) if partial matches (40-79)
        (None, []) if no matches
    """
    results = await search_baths(db, query, limit=5)
    if not results:
        return None, []
    best_bath, best_score = results[0]
    if best_score >= 80:
        return best_bath, []
    elif best_score >= 40:
        return None, results
    return None, []


async def create_bath(
    db: AsyncSession,
    name: str,
    country_id: int | None = None,
    region_id: int | None = None,
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    url: str | None = None,
    description: str | None = None,
) -> Bath:
    bath = Bath(
        name=name,
        aliases=[],
        country_id=country_id,
        region_id=region_id,
        city=city,
        lat=lat,
        lng=lng,
        url=url,
        description=description,
    )
    db.add(bath)
    await db.commit()
    await db.refresh(bath)
    return bath


async def merge_baths(db: AsyncSession, source_id: int, target_id: int) -> Bath:
    """Move all visits from source to target, archive source."""
    from app.db.models.visit import Visit

    await db.execute(
        update(Visit).where(Visit.bath_id == source_id).values(bath_id=target_id)
    )
    source_q = await db.execute(select(Bath).where(Bath.id == source_id))
    source = source_q.scalar_one()
    source.canonical_id = target_id
    source.is_archived = True
    await db.commit()

    target_q = await db.execute(select(Bath).where(Bath.id == target_id))
    return target_q.scalar_one()


async def get_all_countries(db: AsyncSession) -> list[Country]:
    result = await db.execute(select(Country).order_by(Country.name))
    return result.scalars().all()


async def get_regions_by_country(db: AsyncSession, country_id: int) -> list[Region]:
    result = await db.execute(
        select(Region).where(Region.country_id == country_id).order_by(Region.name)
    )
    return result.scalars().all()
