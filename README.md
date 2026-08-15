# Gait Forensics AI - Biometric Gait Recognition System

An AI-powered forensic gait-recognition application that analyzes human walking patterns from video and image sequences to determine identity profiles. The project uses standard computer vision techniques (OpenCV) for video preprocessing and human silhouette extraction, combined with a deep learning temporal model (PyTorch CNN-LSTM) to perform classification. A modern, interactive analytics dashboard (React + Tailwind CSS) displays biometrics, frame-by-frame extractions, training metrics, and printable forensic reports.

---

## 🎥 Key Features

- **Gait Preprocessing Engine:** Extract walk frames, apply background subtraction (MOG2), center and normalize silhouettes to $64 \times 64$ dimensions.
- **Biometric Signature Generation:** Compute the **Gait Energy Image (GEI)** — the average silhouette density signature representing individual kinematic profiles.
- **Deep Learning Sequence Classifier:** Dual spatial-temporal mapping using a 2D CNN encoder and a recurrent LSTM layer.
- **Forensic Investigation Dashboard:**
  - **Live Analyzer:** Upload walk clips, watch the pipeline processing step-by-step, view the frame slider, and read prediction confidence ranks.
  - **Dataset Registry:** Enroll and manage subject profiles with custom biometrics (Height, Stride, Cadence).
  - **Model Training Center:** Track accuracy and loss metrics on training/validation datasets with interactive line charts.
  - **Forensic Report Architect:** Generate formal biometrics audit documents optimized for printing or PDF exports.

---

## 📂 Project Directory Structure

```text
Gait-Forensics-AI/
├── frontend/                 # React SPA (Vite, Tailwind, Recharts, Lucide, Framer Motion)
│   ├── src/
│   │   ├── App.jsx           # Main Dashboard and wizard pages
│   │   ├── main.jsx
│   │   └── index.css         # Tailwind styles & forensic animations
│   ├── tailwind.config.js
│   └── package.json
│
├── backend/                  # FastAPI web server
│   ├── main.py               # REST API endpoints & production static serving
│   ├── database.py           # Database wrapper (Dual SQLite and MongoDB support)
│   ├── preprocessing.py      # OpenCV video frame segmenter and GEI builder
│   └── model_inference.py    # PyTorch inference controller
│
├── model/                    # Deep learning model codebase
│   ├── gait_net.py           # CNN-LSTM architecture definition
│   ├── train.py              # PyTorch model training runner
│   ├── generate_synthetic_data.py # Synthetic silhouette generator for training
│   └── training_metrics.json # Saved accuracy and loss history (loaded by frontend)
│
├── dataset/                  # Synthetic training, validation, and testing divisions
├── Dockerfile                # Multi-stage production container
└── requirements.txt          # Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**

---

### Step 1: Install Python Dependencies & Generate Model

1. Open your terminal in the project root and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(For CPU-only machines, you can install the lightweight PyTorch builds using: `pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision`)*

2. Run the synthetic dataset generator and train the PyTorch model (runs for 10 epochs):
   ```bash
   python model/train.py
   ```
   This will:
   - Generate walking silhouettes under `dataset/`
   - Train the CNN-LSTM model
   - Save model weights to `model/gait_model.pth` and training charts history to `model/training_metrics.json`.

---

### Step 2: Set Up React Frontend

1. Navigate to the `frontend/` directory and install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`.

---

### Step 3: Run the FastAPI Backend Server

1. From the project root, start the FastAPI server:
   ```bash
   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```
   The backend API will run at `http://localhost:8000` (docs available at `/docs`).

---

## 🐋 Running with Docker

Deploy both frontend and backend automatically using the optimized multi-stage build:

1. Build the Docker image:
   ```bash
   docker build -t gait-forensics-ai .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 gait-forensics-ai
   ```
   Open `http://localhost:8000` in your web browser. The backend will automatically serve both the React build assets and the API endpoints on a single port!

---

## 💾 Database Configuration

The application features a unified database layer:
- **SQLite (Default):** Zero configuration. Automatically creates a local file `gait_forensics.db` inside the project root directory.
- **MongoDB:** To run with MongoDB, set the `MONGODB_URI` environment variable before launching the backend:
  ```bash
  export MONGODB_URI="mongodb://localhost:27017"
  ```
  The database repository layer will automatically detect the presence of the URI and transition from SQLite to MongoDB collections.
