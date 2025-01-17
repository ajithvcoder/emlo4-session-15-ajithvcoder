import io
import socket
import logging
import requests
import torch
import timm

from PIL import Image
from fastapi import FastAPI, File
from fastapi.middleware.cors import CORSMiddleware
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

HOSTNAME = socket.gethostname()

@app.on_event("startup")
async def initialize():
    global model, device, transform, labels

    logger.info(f"Initializing model server on host {HOSTNAME}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # Create model
    logger.info("Loading model: mambaout_base.in1k")
    model = timm.create_model("mambaout_base.in1k", pretrained=True)
    model = model.to(device)
    model.eval()
    logger.info("Model loaded successfully")

    # Get model specific transforms
    logger.info("Setting up model transforms")
    data_config = timm.data.resolve_model_data_config(model)
    transform = timm.data.create_transform(**data_config, is_training=False)

    # Load ImageNet labels
    logger.info("Loading ImageNet categories")
    url = "https://storage.googleapis.com/bit_models/ilsvrc2012_wordnet_lemmas.txt"
    labels = requests.get(url).text.strip().split("\n")
    logger.info(f"Loaded {len(labels)} categories")

@torch.no_grad()
def predict(img: Image.Image) -> Dict[str, float]:
    logger.debug("Starting prediction")
    img = img.convert("RGB")
    img_tensor = transform(img).unsqueeze(0).to(device)

    # inference
    logger.debug("Running inference")
    output = model(img_tensor)
    probabilities = torch.nn.functional.softmax(output[0], dim=0)

    # Get top 5 predictions
    top5_prob, top5_catid = torch.topk(probabilities, 5)
    predictions = {
        labels[idx.item()]: float(prob) for prob, idx in zip(top5_prob, top5_catid)
    }

    logger.debug(f"Prediction complete. Top class: {list(predictions.keys())[0]}")
    return predictions

@app.post("/infer")
async def infer(image: Annotated[bytes, File()]):
    """
    Endpoint for image classification.
    Accepts an image file and returns top 5 predictions with their probabilities.
    """
    logger.info("Received inference request")
    img = Image.open(io.BytesIO(image))

    logger.debug("Running prediction")
    predictions = predict(img)

    logger.info("Inference complete")
    return predictions

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "hostname": HOSTNAME,
        "model": "mambaout_base.in1k",
        "device": str(device) if "device" in globals() else None,
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
