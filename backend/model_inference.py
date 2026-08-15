import os
import torch
import numpy as np
import json
from model.gait_net import GaitNet
from backend.database import db

# Load mapping of classes from DB
def get_class_mappings():
    subjects = db.get_subjects()
    # E.g., [ {"id": "subject_001", "name": "John Doe"}, ... ]
    id_to_name = {s["id"]: s["name"] for s in subjects}
    idx_to_id = {i: s["id"] for i, s in enumerate(subjects)}
    return id_to_name, idx_to_id

class GaitPredictor:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.num_classes = 10
        self.id_to_name = {}
        self.idx_to_id = {}
        
        self.load_model()
        
    def load_model(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.abspath(os.path.join(script_dir, "..", "model", "gait_model.pth"))
        
        try:
            self.id_to_name, self.idx_to_id = get_class_mappings()
            self.num_classes = len(self.idx_to_id) if self.idx_to_id else 10
            
            self.model = GaitNet(num_classes=self.num_classes)
            if os.path.exists(model_path):
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                print(f"Loaded trained model weights from {model_path}")
            else:
                print(f"Model weights not found at {model_path}. Running in demo/inference mode.")
            self.model.to(self.device)
            self.model.eval()
        except Exception as e:
            print(f"Error loading model: {e}. Fallback to mock mode enabled.")
            self.model = None

    def predict(self, silhouette_seq):
        """
        Takes list of 30 silhouette frames (each 64x64) and runs inference.
        Returns:
            - predicted_subject_id (str)
            - predicted_name (str)
            - confidence (float)
            - probabilities (list of dicts)
            - embedding (list)
        """
        # Load mappings again in case subjects were updated in DB
        self.id_to_name, self.idx_to_id = get_class_mappings()
        
        if self.model is None or len(silhouette_seq) < 30:
            return self._mock_predict()
            
        try:
            # Prepare tensor: (1, seq_len, 1, 64, 64)
            frames = []
            for img in silhouette_seq[:30]:
                img_norm = img.astype(np.float32) / 255.0
                img_norm = np.expand_dims(img_norm, axis=0) # 1 x 64 x 64
                frames.append(img_norm)
            
            # Stack and add batch dimension
            seq_tensor = torch.tensor(np.stack(frames, axis=0)).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                logits, embedding = self.model(seq_tensor)
                probabilities = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()
                
            pred_idx = int(np.argmax(probabilities))
            pred_id = self.idx_to_id.get(pred_idx, f"subject_{pred_idx+1:03d}")
            pred_name = self.id_to_name.get(pred_id, f"Unknown Subject {pred_idx+1}")
            confidence = float(probabilities[pred_idx])
            
            # Create list of probabilities for all subjects
            prob_list = []
            for i, p in enumerate(probabilities):
                sub_id = self.idx_to_id.get(i, f"subject_{i+1:03d}")
                sub_name = self.id_to_name.get(sub_id, f"Subject {i+1}")
                prob_list.append({
                    "subject_id": sub_id,
                    "name": sub_name,
                    "probability": round(float(p) * 100, 2)
                })
                
            # Sort by probability descending
            prob_list = sorted(prob_list, key=lambda x: x["probability"], reverse=True)
            
            return pred_id, pred_name, confidence, prob_list, embedding.squeeze(0).cpu().tolist()
            
        except Exception as e:
            print(f"Inference error: {e}. Falling back to mock prediction.")
            return self._mock_predict()

    def _mock_predict(self):
        """
        Fallback simulation of predictions.
        """
        # pick a random subject
        subjects = db.get_subjects()
        if not subjects:
            pred_id = "subject_001"
            pred_name = "John Doe"
        else:
            chosen = np.random.choice(subjects)
            pred_id = chosen["id"]
            pred_name = chosen["name"]
            
        confidence = float(np.random.uniform(0.85, 0.98))
        
        prob_list = []
        remaining = 1.0 - confidence
        
        for s in subjects:
            if s["id"] == pred_id:
                prob = confidence
            else:
                prob = float(np.random.uniform(0.01, remaining / len(subjects) * 2))
            prob_list.append({
                "subject_id": s["id"],
                "name": s["name"],
                "probability": round(prob * 100, 2)
            })
            
        # Re-normalize to sum to 100%
        total_p = sum(p["probability"] for p in prob_list)
        for p in prob_list:
            p["probability"] = round((p["probability"] / total_p) * 100, 2)
            
        prob_list = sorted(prob_list, key=lambda x: x["probability"], reverse=True)
        
        # Mock embedding (64 dim normalized vector)
        mock_emb = (np.random.randn(64) / 10.0).tolist()
        
        return pred_id, pred_name, confidence, prob_list, mock_emb

predictor = GaitPredictor()
