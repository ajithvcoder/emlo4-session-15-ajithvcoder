import urllib
import io
import os
import zlib
import json
import socket
import logging
import requests

import redis.asyncio as redis
# import torch
import onnxruntime as ort
import numpy as np

from PIL import Image
from fastapi import FastAPI, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Dict, Annotated

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - ModelServer - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mamba Model Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Update environment variables
MODEL_NAME = os.environ.get("MODEL_NAME", "mambaout_femto.in1k")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
HOSTNAME = socket.gethostname()
INPUT_SIZE = (224, 224)
MEAN = np.array([0.485, 0.456, 0.406])
STD = np.array([0.229, 0.224, 0.225])
LABELS = ["Cat", "Dog"]

class ModelInference:
    def __init__(self, model_path):
        """
        Initialize ONNX model inference session
        
        Args:
            model_path (str): Path to the ONNX model file
        """
        try:
            print("Loading ONNX model...")
            self.session = ort.InferenceSession(model_path)
            
            # Warm-up inference to ensure model is ready
            self.session.run(
                ["output"], 
                {"input": np.random.randn(1, 3, *INPUT_SIZE).astype(np.float32)}
            )
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            raise

    def preprocess_image(self, image: Image.Image) -> np.ndarray:
        """
        Preprocess image for model inference
        
        Args:
            image (PIL.Image): Input image
        
        Returns:
            np.ndarray: Preprocessed image array
        """
        # Convert to RGB and resize
        image = image.convert("RGB").resize(INPUT_SIZE)
        
        # Convert to numpy array and normalize
        img_array = np.array(image).astype(np.float32) / 255.0
        
        # Apply mean and std normalization
        img_array = (img_array - MEAN) / STD
        
        # Transpose to channel-first format
        img_array = img_array.transpose(2, 0, 1)
        
        # Add batch dimension
        return np.expand_dims(img_array, 0)

    def predict(self, image: Image.Image) -> dict:
        """
        Perform model inference
        
        Args:
            image (PIL.Image): Input image
        
        Returns:
            dict: Prediction probabilities
        """
        processed_image = self.preprocess_image(image)
        
        outputs = self.session.run(
            ["output"], 
            {"input": processed_image.astype(np.float32)}
        )
        
        # Process logits to probabilities
        logits = outputs[0][0]
        probabilities = np.exp(logits) / np.sum(np.exp(logits))
        
        return {LABELS[i]: float(prob) for i, prob in enumerate(probabilities)}


@app.on_event("startup")
async def initialize():
    global model, device, transform, categories, redis_pool

    logger.info(f"Initializing model server on host {HOSTNAME}")
    logger.info(f"Loading model: {MODEL_NAME}")
    model = ModelInference("mambaout_model.onnx")
    # model = model.to(device)
    # model.eval()
    logger.info(f"Model loaded successfully")

    # Redis setup
    logger.info(f"Creating Redis connection pool: host={REDIS_HOST}, port={REDIS_PORT}")
    redis_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=0,
        decode_responses=True,
    )
    logger.info("Model server initialization complete")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup connection pool on shutdown"""
    logger.info("Shutting down model server")
    await redis_pool.aclose()
    logger.info("Cleanup complete")

def get_redis():
    return redis.Redis(connection_pool=redis_pool)

def predict(inp_img: Image) -> Dict[str, float]:
    logger.debug("Starting prediction")
    img = inp_img.convert("RGB")
    result = {"response": "error"}
    # inference

    logger.debug("Running inference")
    predictions = model.predict(img)
    top_class = max(predictions, key=predictions.get)
    confidence = predictions[top_class]

    result = {"class": top_class, "confidence": confidence}

    logger.info(f"Prediction complete. Top class: {result}")
    return result

async def write_to_cache(file: bytes, result: Dict[str, float]) -> None:
    cache = get_redis()
    hash = str(zlib.adler32(file))
    logger.debug(f"Writing prediction to cache with hash: {hash}")
    await cache.set(hash, json.dumps(result))
    logger.debug("Cache write complete")

@app.post("/infer")
async def infer(image: Annotated[bytes, File()]):
    
    logger.info("Received inference request")
    img: Image.Image = Image.open(io.BytesIO(image))

    logger.debug("Running prediction")
    predictions = predict(img)

    logger.debug("Writing results to cache")
    await write_to_cache(image, predictions)

    logger.info("Inference complete")
    return predictions

@app.get("/health")
async def health_check():
    try:
        redis_client = get_redis()
        redis_connected = await redis_client.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        redis_connected = False

    return {
        "status": "healthy",
        "hostname": HOSTNAME,
        "model": MODEL_NAME,
        "device": str(device) if "device" in globals() else None,
        "redis": {
            "host": REDIS_HOST,
            "port": REDIS_PORT,
            "connected": redis_connected,
        },
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
