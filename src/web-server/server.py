import os
import zlib
import json
import logging
import socket
import traceback

import redis.asyncio as redis
import httpx

from fastapi import FastAPI, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Annotated

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - WebServer - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Web Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add constants
HOSTNAME = socket.gethostname()
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
MODEL_SERVER_URL = os.environ.get("MODEL_SERVER_URL", "http://localhost:80")
# MODEL_SERVER_URL = "http://model-server-service"

@app.on_event("startup")
async def initialize():
    global redis_pool
    logger.info(f"Initializing web server on host {HOSTNAME}")
    logger.info(f"Creating Redis connection pool: host={REDIS_HOST}, port={REDIS_PORT}")
    redis_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=0,
        decode_responses=True,
    )
    logger.info("Web server initialization complete")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup connection pool on shutdown"""
    logger.info("Shutting down web server")
    await redis_pool.aclose()
    logger.info("Cleanup complete")

def get_redis():
    return redis.Redis(connection_pool=redis_pool)

async def check_cached(image: bytes):
    hash = zlib.adler32(image)
    cache = get_redis()

    logger.debug(f"Checking cache for image hash: {hash}")
    data = await cache.get(hash)

    if data:
        logger.info(f"Cache hit for image hash: {hash}")
    else:
        logger.info(f"Cache miss for image hash: {hash}")

    return json.loads(data) if data else None

@app.post("/classify-catdog")
async def classify_catdog(image: Annotated[bytes, File()]):
    logger.info("Received classification request")
    logger.info("MODEL_SERVER_URL-", MODEL_SERVER_URL)
    infer_cache = await check_cached(image)
    # infer_cache = None
    if infer_cache == None:
        logger.info("Making request to model server")
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            try:
                url = f"{MODEL_SERVER_URL}/infer"
                files = {"image": image}
                logger.info("sending files")
                logger.debug(f"Sending request to model server: {url}")
                response = await client.post(url, files=files)
                logger.info("got response")
                response.raise_for_status()

                logger.info("Successfully received model prediction")
                return response.json()
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Model server request failed: {str(e)}")
                raise HTTPException(status_code=500, detail="Error from Model Endpoint")

    return infer_cache

@app.get("/health")
async def health_check():
    """Health check endpoint for kubernetes readiness/liveness probes"""
    try:
        # Test Redis connection
        redis_client = get_redis()
        redis_connected = await redis_client.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        redis_connected = False

    try:
        # Test Model Server connection
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.get(f"{MODEL_SERVER_URL}/health")
            response.raise_for_status()
            model_health = response.json()
            model_connected = True
    except Exception as e:
        logger.error(f"Model server health check failed: {str(e)}")
        model_connected = False
        model_health = None

    health_status = {
        "status": "healthy" if (redis_connected and model_connected) else "degraded",
        "hostname": HOSTNAME,
        "redis": {"host": REDIS_HOST, "port": REDIS_PORT, "connected": redis_connected},
        "model_server": {
            "url": MODEL_SERVER_URL,
            "connected": model_connected,
            "health": model_health,
        },
    }

    logger.info(f"Health check status: {health_status['status']}")
    return health_status

# uvicorn server:app --host 0.0.0.0 --port 9000 --reload

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)