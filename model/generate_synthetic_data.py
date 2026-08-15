import os
import cv2
import numpy as np
import random
import shutil

def create_gait_silhouette(frame_idx, height, width, stride_amp, cycle_len, noise_level=0.0):
    """
    Synthesizes a 64x64 binary silhouette frame of a person walking.
    """
    canvas = np.zeros((64, 64), dtype=np.uint8)
    
    # Core body parameters
    center_x = 32
    head_r = int(height * 0.1)
    torso_h = int(height * 0.4)
    leg_h = height - head_r*2 - torso_h
    
    head_y = 12 + head_r
    torso_top_y = head_y + head_r
    torso_bot_y = torso_top_y + torso_h
    
    # Walking cycle phase (sine wave for leg swing)
    phase = (2 * np.pi * frame_idx) / cycle_len
    leg1_swing = np.sin(phase) * stride_amp
    leg2_swing = -np.sin(phase) * stride_amp
    
    # 1. Draw head
    cv2.circle(canvas, (center_x, head_y), head_r, 255, -1)
    
    # 2. Draw torso (as an ellipse/rectangle for girth)
    cv2.ellipse(canvas, (center_x, torso_top_y + torso_h // 2), 
                (width // 2, torso_h // 2), 0, 0, 360, 255, -1)
    
    # 3. Draw legs
    # Leg 1
    l1_x = int(center_x + leg1_swing)
    cv2.line(canvas, (center_x, torso_bot_y), (l1_x, torso_bot_y + leg_h), 255, width // 3 + 1)
    
    # Leg 2
    l2_x = int(center_x + leg2_swing)
    cv2.line(canvas, (center_x, torso_bot_y), (l2_x, torso_bot_y + leg_h), 255, width // 3 + 1)
    
    # 4. Draw arms (moving opposite to legs)
    arm1_swing = -np.sin(phase) * (stride_amp * 0.6)
    arm2_swing = np.sin(phase) * (stride_amp * 0.6)
    
    a1_x = int(center_x + arm1_swing)
    cv2.line(canvas, (center_x, torso_top_y + 3), (a1_x, torso_top_y + torso_h // 2 + 5), 255, width // 4 + 1)
    a2_x = int(center_x + arm2_swing)
    cv2.line(canvas, (center_x, torso_top_y + 3), (a2_x, torso_top_y + torso_h // 2 + 5), 255, width // 4 + 1)

    # Apply slight blurring and thresholding to make it organic
    canvas = cv2.GaussianBlur(canvas, (3, 3), 0)
    _, canvas = cv2.threshold(canvas, 100, 255, cv2.THRESH_BINARY)
    
    # Add random translation/noise
    if noise_level > 0:
        dx = random.randint(-1, 1)
        dy = random.randint(-1, 1)
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        canvas = cv2.warpAffine(canvas, M, (64, 64))
        
        # Salt & pepper noise
        noise = np.random.rand(*canvas.shape)
        canvas[noise < (noise_level * 0.05)] = 0
        canvas[noise > (1 - noise_level * 0.05)] = 255
        
    return canvas

def generate_dataset(base_dir="dataset", num_subjects=10, seqs_per_sub=6, frames_per_seq=30):
    """
    Generates train, validation, and test splits for multiple subjects.
    """
    splits = {
        'train': (0, int(seqs_per_sub * 0.6)), # 60%
        'validation': (int(seqs_per_sub * 0.6), int(seqs_per_sub * 0.8)), # 20%
        'test': (int(seqs_per_sub * 0.8), seqs_per_sub) # 20%
    }
    
    # Reset dataset directory
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
        
    # Generate static biometric styles for each subject to keep them unique
    subject_profiles = {}
    for sub_idx in range(1, num_subjects + 1):
        subject_profiles[sub_idx] = {
            'height': random.randint(38, 48),
            'width': random.randint(10, 16),
            'stride_amp': random.randint(6, 12),
            'cycle_len': random.randint(14, 22)
        }
    
    for split_name, (start_seq, end_seq) in splits.items():
        print(f"Generating {split_name} split...")
        for sub_idx in range(1, num_subjects + 1):
            sub_name = f"subject_{sub_idx:03d}"
            profile = subject_profiles[sub_idx]
            
            for seq_idx in range(start_seq, end_seq):
                seq_name = f"walk_{seq_idx:02d}"
                seq_dir = os.path.join(base_dir, split_name, sub_name, seq_name)
                os.makedirs(seq_dir, exist_ok=True)
                
                # Introduce slight variation per sequence
                seq_height = profile['height'] + random.randint(-1, 1)
                seq_width = profile['width'] + random.randint(-1, 1)
                seq_stride = profile['stride_amp'] + random.randint(-1, 1)
                seq_cycle = profile['cycle_len'] + random.randint(-1, 1)
                
                for f_idx in range(frames_per_seq):
                    # Add noise for training, less for test/validation
                    noise = 0.2 if split_name == 'train' else 0.05
                    frame = create_gait_silhouette(
                        f_idx, 
                        seq_height, 
                        seq_width, 
                        seq_stride, 
                        seq_cycle, 
                        noise_level=noise
                    )
                    cv2.imwrite(os.path.join(seq_dir, f"frame_{f_idx:03d}.png"), frame)
                    
    print("Dataset generation complete!")

if __name__ == "__main__":
    generate_dataset(num_subjects=10)
