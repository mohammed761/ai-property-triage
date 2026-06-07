import os
import requests
import time

API_KEY = "YeudFsMrH1TiUkaB4Jc7qG6iHUK1Shl7MtYYpzU2QKnHqaugld4STh4A"
URL = "https://api.pexels.com/v1/search"

headers = {
    "Authorization": API_KEY
}

# 🏠 ALL ROOM TYPES
categories = [
    "bathroom",
    "bedroom",
    "exterior",
    "kitchen",
    "living_room",
    "other"
]

BASE_DIR = os.path.join("real-estate-ai", "image_service", "dataset","val")

IMAGES_PER_CLASS = 40

for category in categories:
    print(f"\n📥 Downloading: {category}")

    output_dir = os.path.join(BASE_DIR, category)
    os.makedirs(output_dir, exist_ok=True)

    params = {
        "query": category,
        "per_page": IMAGES_PER_CLASS
    }

    response = requests.get(URL, headers=headers, params=params)
    data = response.json()

    photos = data.get("photos", [])

    for i, photo in enumerate(photos):
        try:
            img_url = photo["src"]["large"]
            img_data = requests.get(img_url).content

            file_path = os.path.join(output_dir, f"{category}_{i+1}.jpg")

            with open(file_path, "wb") as f:
                f.write(img_data)

            print(f"Downloaded {file_path}")

        except Exception as e:
            print(f"Error downloading image {i}: {e}")

    time.sleep(1)  # avoid API rate limit

print("\n✅ DONE: All categories downloaded!")