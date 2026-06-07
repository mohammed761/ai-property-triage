import pandas as pd
from PIL import Image
from torch.utils.data import Dataset

class PropertyDataset(Dataset):

    def __init__(self, csv_file, class_map, transform=None):
        self.data = pd.read_csv(csv_file)
        self.transform = transform
        self.class_map = class_map

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):

        row = self.data.iloc[idx]

        img_path = "../dataset/train/" + row["image"]

        image = Image.open(img_path).convert("RGB")

        label = self.class_map[row["label"]]
        condition = float(row["condition"])

        if self.transform:
            image = self.transform(image)

        return image, label, condition