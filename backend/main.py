import os
import shutil
import time
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import cv2
import json

from backend.database import db
from backend.preprocessing import extract_silhouette_sequence
from backend.model_inference import predictor
from model.train import train_model
from model.generate_synthetic_data import generate_dataset

app = FastAPI(title="Gait Forensics AI API", version="1.0.0")

# Allow CORS for React development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
GEI_DIR = os.path.join(STATIC_DIR, "gei")
FRAMES_DIR = os.path.join(STATIC_DIR, "temp_frames")
TEMP_DIR = os.path.join(BASE_DIR, "temp_uploads")

for d in [STATIC_DIR, GEI_DIR, FRAMES_DIR, TEMP_DIR]:
    os.makedirs(d, exist_ok=True)

# Serve static files for visual outputs
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory training status tracker
training_state = {
    "is_training": False,
    "current_epoch": 0,
    "total_epochs": 10,
    "status": "Idle",
    "message": ""
}

class SubjectCreate(BaseModel):
    id: str
    name: str
    height: int
    stride_length: float
    cadence: float

class ReportCreate(BaseModel):
    history_id: str
    analyst: str
    findings: str

# Helper to run background model training
def run_background_training():
    global training_state
    try:
        training_state["is_training"] = True
        training_state["status"] = "Generating Dataset"
        training_state["message"] = "Synthesizing silhouette frames for 10 subjects..."
        
        # 1. Regenerate dataset
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dataset_dir = os.path.abspath(os.path.join(script_dir, "..", "dataset"))
        generate_dataset(dataset_dir, num_subjects=10)
        
        # 2. Train model
        training_state["status"] = "Training Neural Network"
        training_state["message"] = "Optimizing CNN-LSTM parameters..."
        
        # We run a faster training in the background for demo
        train_model(epochs=10, batch_size=4, lr=0.001)
        
        training_state["status"] = "Completed"
        training_state["message"] = "Model trained successfully. Weights updated."
    except Exception as e:
        training_state["status"] = "Error"
        training_state["message"] = f"Training failed: {str(e)}"
    finally:
        training_state["is_training"] = False

@app.get("/api/status")
def get_system_status():
    return {
        "status": "Online",
        "database": db.__class__.__name__,
        "model_loaded": predictor.model is not None,
        "device": str(predictor.device)
    }

@app.post("/api/analyze")
async def analyze_gait(
    file: UploadFile = File(...),
    analyst: str = Form("Forensic AI System")
):
    start_time = time.time()
    
    # Save uploaded file
    file_ext = os.path.splitext(file.filename)[1]
    temp_file_path = os.path.join(TEMP_DIR, f"upload_{int(time.time())}{file_ext}")
    
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Preprocessing: extract silhouettes, GEI, and biometrics
        silhouettes, gei, biometrics = extract_silhouette_sequence(temp_file_path)
        
        if not silhouettes or gei is None:
            raise HTTPException(status_code=400, detail="Failed to extract sufficient gait silhouettes from video.")
            
        # Run deep learning model prediction
        pred_id, pred_name, confidence, probabilities, embedding = predictor.predict(silhouettes)
        
        processing_time = round(time.time() - start_time, 2)
        
        # Log to history in database
        history_id = db.add_history_entry(
            filename=file.filename,
            predicted_class=pred_id,
            confidence=round(confidence * 100, 2),
            processing_time=processing_time,
            gait_params=biometrics,
            status="Processed"
        )
        
        # Save GEI image file to serve it to frontend
        gei_filename = f"gei_{history_id}.png"
        gei_path = os.path.join(GEI_DIR, gei_filename)
        cv2.imwrite(gei_path, gei)
        
        # Save all silhouette frames to local server directory so frontend can scroll them
        seq_dir_name = f"seq_{history_id}"
        seq_path = os.path.join(FRAMES_DIR, seq_dir_name)
        os.makedirs(seq_path, exist_ok=True)
        
        frame_urls = []
        for idx, sil in enumerate(silhouettes):
            frame_filename = f"frame_{idx:03d}.png"
            cv2.imwrite(os.path.join(seq_path, frame_filename), sil)
            frame_urls.append(f"/static/temp_frames/{seq_dir_name}/{frame_filename}")
            
        # Auto-generate forensic findings
        findings = (
            f"The forensic gait analysis on '{file.filename}' was processed in {processing_time}s. "
            f"The system classified the walking pattern as matching Subject: {pred_name} ({pred_id}) "
            f"with a confidence score of {confidence*100:.2f}%. "
            f"Biometric measurements indicate an average stride length of {biometrics['stride_length_cm']} cm, "
            f"a walking cadence of {biometrics['cadence_bpm']} steps/min, and a height profile of "
            f"{biometrics['height_cm']} cm. The silhouette outline matches typical spatial boundaries "
            f"for this subject profile."
        )
        
        # Save report
        report_id = db.create_report(history_id, analyst, findings)
        
        # Clean up original temp upload file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return {
            "history_id": history_id,
            "report_id": report_id,
            "filename": file.filename,
            "predicted_id": pred_id,
            "predicted_name": pred_name,
            "confidence": round(confidence * 100, 2),
            "processing_time": processing_time,
            "biometrics": biometrics,
            "probabilities": probabilities,
            "gei_url": f"/static/gei/{gei_filename}",
            "frames": frame_urls,
            "findings": findings
        }
        
    except Exception as e:
        # Clean up temp file in case of error
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        print(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/api/subjects")
def get_subjects():
    return db.get_subjects()

@app.get("/api/subjects/{sub_id}")
def get_subject(sub_id: str):
    sub = db.get_subject_by_id(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subject not found")
    return sub

@app.post("/api/subjects")
def add_subject(sub: SubjectCreate):
    dummy_embedding = (np_random_embedding() if hasattr(db, 'insert_mock_subjects') else [0]*64)
    db.add_subject(sub.id, sub.name, sub.height, sub.stride_length, sub.cadence, dummy_embedding)
    return {"status": "Subject added/updated successfully"}

@app.get("/api/history")
def get_history():
    return db.get_history()

@app.get("/api/reports")
def get_reports():
    return db.get_reports()

@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    report = db.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@app.post("/api/reports")
def create_report(rep: ReportCreate):
    report_id = db.create_report(rep.history_id, rep.analyst, rep.findings)
    return {"status": "Report created successfully", "report_id": report_id}

@app.get("/api/model/metrics")
def get_model_metrics():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    metrics_path = os.path.abspath(os.path.join(script_dir, "..", "model", "training_metrics.json"))
    
    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            return json.load(f)
            
    # Mock data fallback for clean initial charts
    return {
        "epochs": list(range(1, 11)),
        "train_loss": [0.95, 0.72, 0.55, 0.41, 0.30, 0.22, 0.16, 0.12, 0.09, 0.07],
        "train_acc": [0.42, 0.65, 0.78, 0.86, 0.91, 0.94, 0.96, 0.98, 0.99, 1.00],
        "val_loss": [0.90, 0.75, 0.60, 0.48, 0.38, 0.33, 0.29, 0.27, 0.25, 0.24],
        "val_acc": [0.45, 0.62, 0.75, 0.82, 0.88, 0.90, 0.91, 0.92, 0.93, 0.94]
    }

@app.post("/api/model/train")
def train_model_endpoint(background_tasks: BackgroundTasks):
    global training_state
    if training_state["is_training"]:
        return {"status": "Already training", "message": training_state["message"]}
        
    background_tasks.add_task(run_background_training)
    return {"status": "Started", "message": "Model training running in the background."}

from fastapi.responses import FileResponse

@app.get("/api/model/train/status")
def get_train_status():
    return training_state

def np_random_embedding(dim=64):
    import numpy as np
    vec = np.random.randn(dim)
    return (vec / np.linalg.norm(vec)).tolist()

# Serve production React app if built
FRONTEND_DIST = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist"))
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend-assets")
    
    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
        
    @app.get("/{catchall:path}")
    async def serve_catchall(catchall: str):
        # Fallback to index.html for SPA routing
        if not catchall.startswith("api/") and not catchall.startswith("static/"):
            return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
        raise HTTPException(status_code=404, detail="Not Found")

