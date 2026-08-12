from fastapi import APIRouter


router = APIRouter()


@router.get("/scaffold")
async def services_scaffold() -> dict:
    return {"module": "services", "ready": True}
