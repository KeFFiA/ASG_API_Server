from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(
    prefix="/status",
    tags=["Status"]
)


@router.get("/")
async def status():
    return FileResponse("D:\PycharmProjects\ASG_ComputerView\Apps\Claims\Server\Routers\data.json", media_type="application/json", filename="data.json")
