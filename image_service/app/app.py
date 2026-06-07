from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel
from PIL import Image
import requests
from io import BytesIO
import torch
import torch.nn as nn
from torchvision import transforms, models
import sys

app = FastAPI()
MODEL_PATH = Path(__file__).resolve().parent / "best_model.pth"

# ======================
# LABELS
# ======================
ROOM_CLASSES = [
    "bathroom",
    "bedroom",
    "exterior",
    "kitchen",
    "living_room",
    "other"
]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ======================
# BACKBONE
# ======================
backbone = models.efficientnet_b0(pretrained=False)
in_features = backbone.classifier[1].in_features
backbone.classifier = nn.Identity()

# ======================
# MODEL (SAME AS TRAINING)
# ======================
class PropertyModel(nn.Module):
    def __init__(self, backbone):
        super().__init__()
        self.backbone = backbone
        self.shared = nn.Sequential(
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        self.room_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, len(ROOM_CLASSES))
        )
        self.condition_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.backbone(x)
        x = self.shared(x)
        room_out = self.room_head(x)
        condition_out = self.condition_head(x)
        return room_out, condition_out.squeeze(1)

# ======================
# LOAD MODEL
# ======================
net = PropertyModel(backbone).to(device)
net.load_state_dict(torch.load(MODEL_PATH, map_location=device))
net.eval()

# ======================
# IMAGE TRANSFORM
# ======================
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# ======================
# REQUEST MODEL (MULTI IMAGE)
# ======================
class RequestData(BaseModel):
    image_urls: list[str]

# ======================
# API
# ======================
@app.get("/health")
def health_check():
    return {
        "service": "image_service",
        "status": "ok",
        "model_loaded": MODEL_PATH.exists(),
        "device": str(device),
    }


@app.post("/analyse")
def analyse(data: RequestData):
    results = []

    print(f"\n🚀 [IMAGE ANALYSER] Received batch of {len(data.image_urls)} image(s) for analysis.", file=sys.stderr)

    for i, url in enumerate(data.image_urls, 1):
        try:
            # Download and process image
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")

            x = transform(image).unsqueeze(0).to(device)

            with torch.no_grad():
                room_logits, condition_raw = net(x)

                # ROOM PREDICTION
                probs = torch.softmax(room_logits, dim=1)
                confidence, predicted = torch.max(probs, dim=1)
                confidence = confidence.item()

                if confidence < 0.40:
                    room_type = "other"
                else:
                    room_type = ROOM_CLASSES[predicted.item()]

                # CONDITION SCORE (0–5)
                condition_score = condition_raw.item() * 5.0

            img_result = {
                "image_url": url,
                "room_type": room_type,
                "condition_score": round(condition_score, 2),
                "confidence": round(confidence, 2)
            }
            results.append(img_result)

            # 🟢 PRINT SUCCESS LOG TO TERMINAL
            print(f"📸 [IMAGE {i}/{len(data.image_urls)}] - SUCCESS", file=sys.stderr)
            print(f"   ↳ URL: {url}", file=sys.stderr)
            print(f"   ↳ Predicted Room: {room_type} (Conf: {round(confidence, 2)})", file=sys.stderr)
            print(f"   ↳ Condition Score: {round(condition_score, 2)}/5.0", file=sys.stderr)

        except Exception as e:
            err_result = {
                "image_url": url,
                "error": str(e)
            }
            results.append(err_result)

            # 🔴 PRINT ERROR LOG TO TERMINAL
            print(f"❌ [IMAGE {i}/{len(data.image_urls)}] - FAILED", file=sys.stderr)
            print(f"   ↳ URL: {url}", file=sys.stderr)
            print(f"   ↳ Error Exception: {str(e)}", file=sys.stderr)

    print(f"🏁 [IMAGE ANALYSER] Batch processing complete.\n", file=sys.stderr)
    return {"results": results}
