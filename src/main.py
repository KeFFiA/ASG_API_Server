import uvicorn

from Server import app
from Config import HOST, PORT


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)

