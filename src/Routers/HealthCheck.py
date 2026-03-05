from Config import Router

router = Router(
    prefix="/health",
    tags=["Health"]
)


@router.get("/")
async def health():
    ...
