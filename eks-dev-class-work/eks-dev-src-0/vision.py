import gradio as gr
import torch
import timm
from PIL import Image
import socket

class ImageClassifier:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # Create model and move to appropriate device
        self.model = timm.create_model("mambaout_base.in1k", pretrained=True)
        self.model = self.model.to(self.device)
        self.model.eval()

        # Get model specific transforms
        data_config = timm.data.resolve_model_data_config(self.model)
        self.transform = timm.data.create_transform(**data_config, is_training=False)

        # Load ImageNet labels
        import requests

        url = "https://storage.googleapis.com/bit_models/ilsvrc2012_wordnet_lemmas.txt"
        self.labels = requests.get(url).text.strip().split("\n")

    @torch.no_grad()
    def predict(self, image):
        if image is None:
            return None

        # Preprocess image
        img = Image.fromarray(image).convert("RGB")
        img_tensor = self.transform(img).unsqueeze(0).to(self.device)

        # Get prediction
        output = self.model(img_tensor)
        probabilities = torch.nn.functional.softmax(output[0], dim=0)

        # Get top 5 predictions
        top5_prob, top5_catid = torch.topk(probabilities, 5)

        return {
            self.labels[idx.item()]: float(prob)
            for prob, idx in zip(top5_prob, top5_catid)
        }

# Create classifier instance
classifier = ImageClassifier()

# Get hostname
hostname = socket.gethostname()

# Create Gradio interface with modified launch parameters
demo = gr.Interface(
    fn=classifier.predict,
    inputs=gr.Image(),
    outputs=gr.Label(num_top_classes=5),
    title=f"Basic Image Classification with Mamba - Pod: {hostname}",
    description="Upload an image to classify it using the mambaout_base.in1k model",
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")