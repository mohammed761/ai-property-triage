from pathlib import Path
import csv
import random

BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_PATH = BASE_DIR / "dataset" / "train"
OUTPUT_CSV = BASE_DIR / "dataset" / "condition.csv"

categories = [
    "kitchen",
    "bathroom",
    "bedroom",
    "living_room",
    "exterior",
    "other"
]

rows = []

print("Dataset path:", DATASET_PATH)

for category in categories:
    folder = DATASET_PATH / category

    if not folder.exists():
        print(f"❌ Missing folder: {folder}")
        continue

    for img in folder.iterdir():
        if img.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            rows.append([
                str(img.relative_to(DATASET_PATH)),
                category,
                random.randint(1, 5)   # fake condition
            ])

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["image", "label", "condition"])
    writer.writerows(rows)

print("\n✅ CSV created:", OUTPUT_CSV)
print("Total images:", len(rows))