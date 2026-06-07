import torch
import torch.nn as nn
from torchvision import transforms
from torch.utils.data import DataLoader, random_split
from torch.optim import Adam

from model import PropertyImageModel
from dataset import PropertyDataset

# ======================
# DEVICE
# ======================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ======================
# CLASS MAP
# ======================
class_map = {
    "bathroom": 0,
    "bedroom": 1,
    "exterior": 2,
    "kitchen": 3,
    "living_room": 4,
    "other": 5
}

# ======================
# TRANSFORMS
# ======================
train_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

val_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# ======================
# FULL DATASET (CSV)
# ======================
full_dataset = PropertyDataset(
    "../dataset/condition.csv",
    class_map=class_map,
    transform=train_transforms
)

# ======================
# SPLIT DATASET
# ======================
train_size = int(0.8 * len(full_dataset))
val_size = len(full_dataset) - train_size

train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

# IMPORTANT: validation should NOT use augmentation
val_dataset.dataset.transform = val_transforms

# ======================
# DATALOADERS
# ======================
train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

# ======================
# MODEL
# ======================
net = PropertyImageModel().to(device)

# ======================
# LOSS + OPTIMIZER
# ======================
criterion_cls = nn.CrossEntropyLoss()
criterion_reg = nn.MSELoss()

optimizer = Adam(net.parameters(), lr=0.0005)
lambda_reg = 0.5

# ======================
# TRAINING LOOP
# ======================
EPOCHS = 15
best_val_loss = float("inf")

for epoch in range(EPOCHS):

    # ======================
    # TRAIN
    # ======================
    net.train()

    train_loss = 0
    correct = 0
    total = 0

    for images, labels, conditions in train_loader:

        images = images.to(device)
        labels = labels.to(device)
        conditions = conditions.to(device)

        optimizer.zero_grad()

        logits, cond_out = net(images)

        loss_cls = criterion_cls(logits, labels)
        loss_reg = criterion_reg(cond_out, conditions)

        loss = loss_cls + lambda_reg * loss_reg

        loss.backward()
        optimizer.step()

        train_loss += loss.item()

        preds = torch.argmax(logits, dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    train_acc = correct / total

    # ======================
    # VALIDATION
    # ======================
    net.eval()

    val_loss = 0
    val_correct = 0
    val_total = 0

    with torch.no_grad():
        for images, labels, conditions in val_loader:

            images = images.to(device)
            labels = labels.to(device)
            conditions = conditions.to(device)

            logits, cond_out = net(images)

            loss_cls = criterion_cls(logits, labels)
            loss_reg = criterion_reg(cond_out, conditions)

            loss = loss_cls + lambda_reg * loss_reg

            val_loss += loss.item()

            preds = torch.argmax(logits, dim=1)
            val_correct += (preds == labels).sum().item()
            val_total += labels.size(0)

    val_acc = val_correct / val_total

    # ======================
    # LOG
    # ======================
    print(f"\nEpoch {epoch+1}/{EPOCHS}")
    print(f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc*100:.2f}%")
    print(f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc*100:.2f}%")

    # ======================
    # SAVE BEST MODEL
    # ======================
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(net.state_dict(), "best_model.pth")
        print("Best model saved!")

# ======================
# FINAL SAVE
# ======================
torch.save(net.state_dict(), "final_model.pth")

print("\nTraining completed successfully!")