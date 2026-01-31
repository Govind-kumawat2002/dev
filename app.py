"""
TEST FILE: Face Similarity Search (All-in-One)
Run:
    python test_face_flow.py
Then open:
    http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, File, UploadFile
import uvicorn
import cv2
import numpy as np
from insightface.app import FaceAnalysis
import faiss

# ---------------------------
# Init Model
# ---------------------------
print("Loading face model...")
face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0, det_size=(640, 640))
print("Model loaded")

# ---------------------------
# In-Memory Vector DB
# ---------------------------
DIM = 512
index = faiss.IndexFlatIP(DIM)
stored_names = []

# ---------------------------
# FastAPI App
# ---------------------------
app = FastAPI(title="Face Similarity Flow Test")

@app.get("/")
def home():
    return {
        "status": "OK",
        "faces_in_db": len(stored_names)
    }

# ---------------------------
# ADD FACE
# ---------------------------
@app.post("/add_face")
async def add_face(file: UploadFile = File(...)):
    img_bytes = await file.read()
    img_np = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

    faces = face_app.get(img)
    if len(faces) == 0:
        return {"error": "No face detected"}

    emb = faces[0].embedding.astype("float32")
    index.add(np.array([emb]))
    stored_names.append(file.filename)

    return {
        "message": "Face added",
        "total_faces": len(stored_names)
    }

# ---------------------------
# SEARCH FACE
# ---------------------------
@app.post("/search_face")
async def search_face(file: UploadFile = File(...)):
    if len(stored_names) == 0:
        return {"error": "Database empty"}

    img_bytes = await file.read()
    img_np = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

    faces = face_app.get(img)
    if len(faces) == 0:
        return {"error": "No face detected"}

    emb = faces[0].embedding.astype("float32")
    D, I = index.search(np.array([emb]), k=5)

    results = []
    for i, idx in enumerate(I[0]):
        results.append({
            "rank": i+1,
            "image": stored_names[idx],
            "similarity": float(D[0][i])
        })

    return {"matches": results}

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
