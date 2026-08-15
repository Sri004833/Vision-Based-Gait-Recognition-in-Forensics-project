import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import cv2

class GaitDataset(Dataset):
    """
    Loads sequences of silhouette frames for training/testing.
    """
    def __init__(self, data_dir, seq_len=30):
        self.data_dir = data_dir
        self.seq_len = seq_len
        self.samples = []
        self.class_to_idx = {}
        
        if not os.path.exists(data_dir):
            return
            
        subjects = sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))])
        self.class_to_idx = {sub: idx for idx, sub in enumerate(subjects)}
        
        for sub in subjects:
            sub_dir = os.path.join(data_dir, sub)
            walks = sorted([d for d in os.listdir(sub_dir) if os.path.isdir(os.path.join(sub_dir, d))])
            
            for walk in walks:
                walk_dir = os.path.join(sub_dir, walk)
                self.samples.append((walk_dir, self.class_to_idx[sub]))
                
    def __len__(self):
        return len(self.samples)
        
    def __getitem__(self, idx):
        walk_dir, label = self.samples[idx]
        
        # Get frame files sorted
        frames_files = sorted([f for f in os.listdir(walk_dir) if f.endswith('.png')])
        
        # Load and pad/truncate frames to match seq_len
        frames = []
        for i in range(self.seq_len):
            if i < len(frames_files):
                frame_path = os.path.join(walk_dir, frames_files[i])
                img = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    img = np.zeros((64, 64), dtype=np.uint8)
            else:
                # Pad with empty frame if video is shorter
                img = np.zeros((64, 64), dtype=np.uint8)
                
            # Normalize to [0, 1] and add channel dimension
            img = img.astype(np.float32) / 255.0
            img = np.expand_dims(img, axis=0) # 1 x 64 x 64
            frames.append(img)
            
        frames = np.stack(frames, axis=0) # seq_len x 1 x 64 x 64
        return torch.tensor(frames), torch.tensor(label, dtype=torch.long)

def train_model(epochs=15, batch_size=4, lr=0.001):
    from gait_net import GaitNet
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.abspath(os.path.join(script_dir, "..", "dataset"))
    
    train_dataset = GaitDataset(os.path.join(dataset_dir, "train"))
    val_dataset = GaitDataset(os.path.join(dataset_dir, "validation"))
    
    if len(train_dataset) == 0:
        print("Dataset not found. Generating synthetic dataset first...")
        from generate_synthetic_data import generate_dataset
        generate_dataset(dataset_dir, num_subjects=10)
        train_dataset = GaitDataset(os.path.join(dataset_dir, "train"))
        val_dataset = GaitDataset(os.path.join(dataset_dir, "validation"))
        
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    num_classes = len(train_dataset.class_to_idx)
    print(f"Loaded {len(train_dataset)} training samples and {len(val_dataset)} validation samples.")
    print(f"Number of subject classes: {num_classes}")
    
    model = GaitNet(num_classes=num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    history = {
        "epochs": [],
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": []
    }
    
    best_acc = 0.0
    
    for epoch in range(1, epochs + 1):
        # Training Phase
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            
            optimizer.zero_grad()
            logits, _ = model(inputs)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item() * inputs.size(0)
            _, predicted = torch.max(logits, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
        epoch_train_loss = running_loss / len(train_dataset)
        epoch_train_acc = correct / total
        
        # Validation Phase
        model.eval()
        val_running_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                logits, _ = model(inputs)
                loss = criterion(logits, labels)
                
                val_running_loss += loss.item() * inputs.size(0)
                _, predicted = torch.max(logits, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
                
        epoch_val_loss = val_running_loss / len(val_dataset)
        epoch_val_acc = val_correct / val_total
        
        print(f"Epoch {epoch}/{epochs}: "
              f"Train Loss: {epoch_train_loss:.4f}, Train Acc: {epoch_train_acc:.4f} | "
              f"Val Loss: {epoch_val_loss:.4f}, Val Acc: {epoch_val_acc:.4f}")
        
        history["epochs"].append(epoch)
        history["train_loss"].append(epoch_train_loss)
        history["train_acc"].append(epoch_train_acc)
        history["val_loss"].append(epoch_val_loss)
        history["val_acc"].append(epoch_val_acc)
        
        # Save best model
        if epoch_val_acc > best_acc:
            best_acc = epoch_val_acc
            torch.save(model.state_dict(), os.path.join(script_dir, "gait_model.pth"))
            
    # Save training metrics history
    metrics_path = os.path.join(script_dir, "training_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(history, f, indent=4)
        
    print(f"Training complete! Model saved to gait_model.pth, metrics to training_metrics.json")

if __name__ == "__main__":
    train_model(epochs=10)
