import torch
import torch.nn as nn
from torchvision import models

NUM_ROOM_CLASSES = 6


class PropertyImageModel(nn.Module):

    def __init__(self):
        super().__init__()

        # =========================
        # PRETRAINED EFFICIENTNET
        # =========================
        backbone = models.efficientnet_b0(pretrained=True)

        # =========================
        # PARTIAL FREEZING (OPTIONAL)
        # =========================
        for param in backbone.features[:5].parameters():
            param.requires_grad = False

        for param in backbone.features[5:].parameters():
            param.requires_grad = True

        # =========================
        # REMOVE CLASSIFIER
        # =========================
        in_features = backbone.classifier[1].in_features
        backbone.classifier = nn.Identity()

        self.backbone = backbone

        # =========================
        # SHARED LAYER
        # =========================
        self.shared = nn.Sequential(
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3)
        )

        # =========================
        # ROOM CLASSIFICATION HEAD
        # =========================
        self.room_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, NUM_ROOM_CLASSES)
        )

        # =========================
        # CONDITION HEAD (FIXED)
        # OUTPUT RANGE: 1 → 5
        # =========================
        self.condition_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 1),
            nn.Sigmoid()   # output 0–1
        )

    def forward(self, x):

        # Backbone features
        features = self.backbone(x)

        # Shared representation
        shared = self.shared(features)

        # Room classification
        room_output = self.room_head(shared)

        # Condition regression (scaled 1–5)
        condition_output = self.condition_head(shared)
        condition_score = condition_output * 4 + 1   # FIX: map 0–1 → 1–5

        return room_output, condition_score.squeeze(1)