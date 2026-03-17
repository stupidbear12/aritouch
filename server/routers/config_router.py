from fastapi import APIRouter, HTTPException

from server.db.database import get_db
from server.models import ConfigProfile
from server.services import config_service

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/defaults")
async def get_defaults():
    return await config_service.get_defaults()


@router.get("/{bed_id}", response_model=ConfigProfile)
async def get_config(bed_id: str):
    db = await get_db()
    profile = await config_service.get_config(db, bed_id)
    if not profile:
        raise HTTPException(status_code=404, detail="config not found")
    return profile


@router.put("/{bed_id}", response_model=ConfigProfile)
async def put_config(bed_id: str, profile: ConfigProfile):
    profile.bed_id = bed_id
    db = await get_db()
    return await config_service.upsert_config(db, profile)
