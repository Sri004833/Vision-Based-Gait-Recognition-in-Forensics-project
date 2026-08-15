import torch
import torch.nn as nn

class GaitCNN(nn.Module):
    """
    A 2D Convolutional Neural Network to extract spatial features 
    from individual silhouette frames (64x64).
    """
    def __init__(self, embed_dim=128):
        super(GaitCNN, self).__init__()
        self.features = nn.Sequential(
            # Input: 1 x 64 x 64
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2), # Output: 16 x 32 x 32
            
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2), # Output: 32 x 16 x 16
            
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2), # Output: 64 x 8 x 8
        )
        self.fc = nn.Sequential(
            nn.Linear(64 * 8 * 8, embed_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3)
        )
        
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

class GaitNet(nn.Module):
    """
    Temporal model combining the GaitCNN spatial encoder with an LSTM 
    to recognize identity based on sequence dynamics.
    """
    def __init__(self, num_classes=10, embed_dim=128, hidden_dim=64):
        super(GaitNet, self).__init__()
        self.cnn = GaitCNN(embed_dim)
        
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            num_layers=1,
            batch_first=True,
            bidirectional=False
        )
        
        # Classification Head
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_classes)
        )
        
    def forward(self, x):
        # Input shape: (batch, seq_len, 1, 64, 64)
        batch_size, seq_len, C, H, W = x.size()
        
        # Collapse batch and seq dims for parallel CNN execution
        x_reshaped = x.view(batch_size * seq_len, C, H, W)
        spatial_features = self.cnn(x_reshaped) # Shape: (batch * seq_len, embed_dim)
        
        # Restore temporal shape: (batch, seq_len, embed_dim)
        temporal_features = spatial_features.view(batch_size, seq_len, -1)
        
        # Process sequence with LSTM
        lstm_out, (hn, cn) = self.lstm(temporal_features)
        
        # Retrieve final hidden state
        # hn shape: (1, batch, hidden_dim) -> squeeze to (batch, hidden_dim)
        gait_embedding = hn.squeeze(0) 
        
        # Classify
        logits = self.fc(gait_embedding)
        
        return logits, gait_embedding

if __name__ == "__main__":
    # Test network with dummy input
    model = GaitNet(num_classes=10)
    # 2 batches, 30 frames, 1 channel, 64x64 images
    dummy_input = torch.randn(2, 30, 1, 64, 64)
    logits, embedding = model(dummy_input)
    print("Logits shape:", logits.shape)
    print("Embedding shape:", embedding.shape)
