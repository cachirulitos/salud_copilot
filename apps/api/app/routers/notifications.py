from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter()

@router.get("/")
async def list_notifications(db: AsyncSession = Depends(get_db)):
    return {"status": "not implemented", "resource": "notifications"}
