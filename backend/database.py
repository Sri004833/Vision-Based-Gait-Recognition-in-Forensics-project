import os
import sqlite3
import json
import datetime
from uuid import uuid4

MONGODB_URI = os.getenv("MONGODB_URI")

class SQLiteDatabase:
    def __init__(self, db_path="gait_forensics.db"):
        self.db_path = db_path
        self.init_db()

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_conn() as conn:
            # Create subjects table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                height INTEGER,
                stride_length REAL,
                cadence REAL,
                embedding TEXT
            )
            """)
            
            # Create prediction history table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                predicted_class TEXT NOT NULL,
                confidence REAL NOT NULL,
                processing_time REAL NOT NULL,
                gait_parameters TEXT,
                status TEXT NOT NULL
            )
            """)
            
            # Create reports table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                history_id TEXT NOT NULL,
                analyst TEXT NOT NULL,
                findings TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(history_id) REFERENCES history(id)
            )
            """)
            conn.commit()

            # Insert mock subjects if empty
            cursor = conn.execute("SELECT COUNT(*) FROM subjects")
            if cursor.fetchone()[0] == 0:
                self.insert_mock_subjects(conn)

    def insert_mock_subjects(self, conn):
        mock_subs = [
            ("subject_001", "John Doe", "2026-08-15 10:00:00", 175, 72.5, 110.2),
            ("subject_002", "Jane Smith", "2026-08-15 11:30:00", 162, 65.1, 115.4),
            ("subject_003", "Robert Chen", "2026-08-15 12:45:00", 180, 78.3, 108.1),
            ("subject_004", "Alice Johnson", "2026-08-15 14:15:00", 168, 68.4, 112.5),
            ("subject_005", "Michael Brown", "2026-08-15 15:30:00", 185, 82.0, 105.0),
            ("subject_006", "Emily Davis", "2026-08-15 16:00:00", 155, 60.2, 118.2),
            ("subject_007", "David Wilson", "2026-08-15 16:30:00", 172, 70.8, 111.0),
            ("subject_008", "Sarah Martinez", "2026-08-15 17:00:00", 164, 66.5, 114.1),
            ("subject_009", "James Taylor", "2026-08-15 17:30:00", 178, 74.2, 109.5),
            ("subject_010", "Linda Thomas", "2026-08-15 18:00:00", 170, 69.1, 113.0)
        ]
        for sub in mock_subs:
            dummy_embedding = json.dumps(np_random_embedding().tolist())
            conn.execute(
                "INSERT INTO subjects VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sub[0], sub[1], sub[2], sub[3], sub[4], sub[5], dummy_embedding)
            )
        conn.commit()

    # Subjects
    def get_subjects(self):
        with self.get_conn() as conn:
            cursor = conn.execute("SELECT * FROM subjects ORDER BY id ASC")
            return [dict(row) for row in cursor.fetchall()]
            
    def get_subject_by_id(self, sub_id):
        with self.get_conn() as conn:
            cursor = conn.execute("SELECT * FROM subjects WHERE id = ?", (sub_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_subject(self, sub_id, name, height, stride_length, cadence, embedding):
        with self.get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO subjects VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sub_id, name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                 height, stride_length, cadence, json.dumps(embedding))
            )
            conn.commit()

    # History
    def get_history(self):
        with self.get_conn() as conn:
            cursor = conn.execute("SELECT * FROM history ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]

    def add_history_entry(self, filename, predicted_class, confidence, processing_time, gait_params, status):
        entry_id = str(uuid4())
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO history VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (entry_id, filename, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 predicted_class, confidence, processing_time, json.dumps(gait_params), status)
            )
            conn.commit()
        return entry_id

    # Reports
    def get_reports(self):
        with self.get_conn() as conn:
            cursor = conn.execute("""
                SELECT r.*, h.filename, h.predicted_class, h.confidence, h.gait_parameters
                FROM reports r
                JOIN history h ON r.history_id = h.id
                ORDER BY r.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_report_by_id(self, report_id):
        with self.get_conn() as conn:
            cursor = conn.execute("""
                SELECT r.*, h.filename, h.predicted_class, h.confidence, h.gait_parameters, h.timestamp
                FROM reports r
                JOIN history h ON r.history_id = h.id
                WHERE r.id = ?
            """, (report_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_report(self, history_id, analyst, findings):
        report_id = str(uuid4())
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO reports VALUES (?, ?, ?, ?, ?)",
                (report_id, history_id, analyst, findings, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
        return report_id

def np_random_embedding(dim=64):
    import numpy as np
    vec = np.random.randn(dim)
    return vec / np.linalg.norm(vec)

class MongoDatabase:
    """
    MongoDB Database connector (Active when MONGODB_URI environment variable is present).
    """
    def __init__(self, uri):
        from pymongo import MongoClient
        self.client = MongoClient(uri)
        self.db = self.client.get_database("gait_forensics")
        self.init_db()

    def init_db(self):
        if self.db.subjects.count_documents({}) == 0:
            mock_subs = [
                {"id": "subject_001", "name": "John Doe", "created_at": "2026-08-15 10:00:00", "height": 175, "stride_length": 72.5, "cadence": 110.2},
                {"id": "subject_002", "name": "Jane Smith", "created_at": "2026-08-15 11:30:00", "height": 162, "stride_length": 65.1, "cadence": 115.4},
                {"id": "subject_003", "name": "Robert Chen", "created_at": "2026-08-15 12:45:00", "height": 180, "stride_length": 78.3, "cadence": 108.1},
                {"id": "subject_004", "name": "Alice Johnson", "created_at": "2026-08-15 14:15:00", "height": 168, "stride_length": 68.4, "cadence": 112.5},
                {"id": "subject_005", "name": "Michael Brown", "created_at": "2026-08-15 15:30:00", "height": 185, "stride_length": 82.0, "cadence": 105.0},
                {"id": "subject_006", "name": "Emily Davis", "created_at": "2026-08-15 16:00:00", "height": 155, "stride_length": 60.2, "cadence": 118.2},
                {"id": "subject_007", "name": "David Wilson", "created_at": "2026-08-15 16:30:00", "height": 172, "stride_length": 70.8, "cadence": 111.0},
                {"id": "subject_008", "name": "Sarah Martinez", "created_at": "2026-08-15 17:00:00", "height": 164, "stride_length": 66.5, "cadence": 114.1},
                {"id": "subject_009", "name": "James Taylor", "created_at": "2026-08-15 17:30:00", "height": 178, "stride_length": 74.2, "cadence": 109.5},
                {"id": "subject_010", "name": "Linda Thomas", "created_at": "2026-08-15 18:00:00", "height": 170, "stride_length": 69.1, "cadence": 113.0}
            ]
            for s in mock_subs:
                s["embedding"] = np_random_embedding().tolist()
                self.db.subjects.insert_one(s)

    def get_subjects(self):
        subs = list(self.db.subjects.find({}, {"_id": 0}))
        for s in subs:
            s["embedding"] = json.dumps(s["embedding"])
        return subs
        
    def get_subject_by_id(self, sub_id):
        sub = self.db.subjects.find_one({"id": sub_id}, {"_id": 0})
        if sub:
            sub["embedding"] = json.dumps(sub["embedding"])
        return sub

    def add_subject(self, sub_id, name, height, stride_length, cadence, embedding):
        self.db.subjects.replace_one(
            {"id": sub_id},
            {
                "id": sub_id,
                "name": name,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "height": height,
                "stride_length": stride_length,
                "cadence": cadence,
                "embedding": embedding
            },
            upsert=True
        )

    def get_history(self):
        hist = list(self.db.history.find({}, {"_id": 0}).sort("timestamp", -1))
        for h in hist:
            h["gait_parameters"] = json.dumps(h["gait_parameters"])
        return hist

    def add_history_entry(self, filename, predicted_class, confidence, processing_time, gait_params, status):
        entry_id = str(uuid4())
        self.db.history.insert_one({
            "id": entry_id,
            "filename": filename,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "predicted_class": predicted_class,
            "confidence": confidence,
            "processing_time": processing_time,
            "gait_parameters": gait_params,
            "status": status
        })
        return entry_id

    def get_reports(self):
        pipeline = [
            {"$lookup": {
                "from": "history",
                "localField": "history_id",
                "foreignField": "id",
                "as": "history_info"
            }},
            {"$unwind": "$history_info"},
            {"$project": {
                "_id": 0,
                "id": 1,
                "history_id": 1,
                "analyst": 1,
                "findings": 1,
                "created_at": 1,
                "filename": "$history_info.filename",
                "predicted_class": "$history_info.predicted_class",
                "confidence": "$history_info.confidence",
                "gait_parameters": "$history_info.gait_parameters"
            }},
            {"$sort": {"created_at": -1}}
        ]
        reports = list(self.db.reports.aggregate(pipeline))
        for r in reports:
            r["gait_parameters"] = json.dumps(r["gait_parameters"])
        return reports

    def get_report_by_id(self, report_id):
        pipeline = [
            {"$match": {"id": report_id}},
            {"$lookup": {
                "from": "history",
                "localField": "history_id",
                "foreignField": "id",
                "as": "history_info"
            }},
            {"$unwind": "$history_info"},
            {"$project": {
                "_id": 0,
                "id": 1,
                "history_id": 1,
                "analyst": 1,
                "findings": 1,
                "created_at": 1,
                "filename": "$history_info.filename",
                "predicted_class": "$history_info.predicted_class",
                "confidence": "$history_info.confidence",
                "gait_parameters": "$history_info.gait_parameters",
                "timestamp": "$history_info.timestamp"
            }}
        ]
        res = list(self.db.reports.aggregate(pipeline))
        if res:
            res[0]["gait_parameters"] = json.dumps(res[0]["gait_parameters"])
            return res[0]
        return None

    def create_report(self, history_id, analyst, findings):
        report_id = str(uuid4())
        self.db.reports.insert_one({
            "id": report_id,
            "history_id": history_id,
            "analyst": analyst,
            "findings": findings,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return report_id

# Instantiate the database class dynamically
db = MongoDatabase(MONGODB_URI) if MONGODB_URI else SQLiteDatabase()
