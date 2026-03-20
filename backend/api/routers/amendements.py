from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Amendement
from db.session import get_session

router = APIRouter()


class AmendementItem(BaseModel):
    id: str
    numero: Optional[str]
    titre: Optional[str]
    date_depot: Optional[str]
    sort: Optional[str]
    depute_id: Optional[str]
    url_an: Optional[str]


@router.get("", response_model=list[AmendementItem])
async def list_amendements(
    depute_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    session: AsyncSession = Depends(get_session),
) -> list[AmendementItem]:
    stmt = select(Amendement).order_by(Amendement.date_depot.desc()).limit(limit).offset(offset)
    if depute_id:
        stmt = stmt.where(Amendement.depute_id == depute_id)

    result = await session.execute(stmt)
    amendements = result.scalars().all()

    return [
        AmendementItem(
            id=a.id,
            numero=a.numero,
            titre=a.titre,
            date_depot=str(a.date_depot) if a.date_depot else None,
            sort=a.sort,
            depute_id=a.depute_id,
            url_an=a.url_an,
        )
        for a in amendements
    ]
