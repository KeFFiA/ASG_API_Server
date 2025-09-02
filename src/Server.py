import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import Routers
app = FastAPI(
    title="AI12 Claims Server",
    description="",
    version="0.1.0",
    docs_url="/api/v1/docs",   # Swagger
    redoc_url="/api/v1/redoc", # ReDoc
    root_path="/api/v1"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(Routers.root)
app.include_router(Routers.health)
app.include_router(Routers.status)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
