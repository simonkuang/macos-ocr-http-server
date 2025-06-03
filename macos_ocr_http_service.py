# macos_ocr_http_service.py

import os
import uuid
import shutil
import sqlite3
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pathlib import Path
import traceback

app = FastAPI()

# === Config ===
STORAGE_DIR = Path("./images")
DB_PATH = Path("./ocr_results.db")
TEMPLATES_DIR = Path("./templates")
STORAGE_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True, parents=True)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Templates ===
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# === SQLite ===
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS ocr_results (
    id TEXT PRIMARY KEY,
    filename TEXT,
    text TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()

# === OCR Function ===
def run_native_ocr(image_path: str) -> str:
    from Vision import VNImageRequestHandler, VNRecognizeTextRequest
    from Foundation import NSDictionary, NSURL
    import Quartz

    results_text = []

    def handler_fn(request, error):
        if error:
            raise Exception(f"OCR error: {error}")
        observations = request.results()
        for obs in observations:
            candidates = obs.topCandidates_(1)
            for c in candidates:
                results_text.append(str(c.string()))

    image_url = NSURL.fileURLWithPath_(str(image_path))
    image_source = Quartz.CGImageSourceCreateWithURL(image_url, None)
    if image_source is None:
        raise ValueError("Failed to create image source")
    cgimg = Quartz.CGImageSourceCreateImageAtIndex(image_source, 0, None)
    if cgimg is None:
        raise ValueError("Could not convert image to CGImage")

    request = VNRecognizeTextRequest.alloc().initWithCompletionHandler_(handler_fn)
    request.setRecognitionLanguages_(["zh-Hans", "zh-Hant", "en-US"])
    request.setRecognitionLevel_(1)

    handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cgimg, NSDictionary.dictionary())
    handler.performRequests_error_([request], None)

    return "\n".join(results_text)

# === API ===
@app.post("/ocr")
def ocr_image(file: UploadFile):
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = STORAGE_DIR / filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        text = run_native_ocr(str(file_path))
        cursor.execute("INSERT INTO ocr_results (id, filename, text, status) VALUES (?, ?, ?, ?)", (file_id, filename, text, "done"))
        conn.commit()
        return {"file_id": file_id, "text": text, "status": "done"}
    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"[ERROR] OCR failed for {file_id}:\n{err_msg}")
        cursor.execute("INSERT INTO ocr_results (id, filename, text, status) VALUES (?, ?, ?, ?)", (file_id, filename, err_msg, "error"))
        conn.commit()
        return {"file_id": file_id, "text": None, "status": "error", "error": str(e)}

@app.get("/result/{file_id}")
def get_result(file_id: str):
    cursor.execute("SELECT text, status FROM ocr_results WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    if not row:
        return {"file_id": file_id, "text": None, "status": "not_found"}
    return {"file_id": file_id, "text": row[0], "status": row[1]}

@app.get("/admin")
def admin_page(request: Request):
    cursor.execute("SELECT id, filename, status FROM ocr_results ORDER BY created_at DESC")
    results = cursor.fetchall()
    return templates.TemplateResponse("admin.html", {"request": request, "results": results})

@app.post("/admin/delete")
def delete_files(request: Request, file_ids: List[str] = Form(...)):
    for fid in file_ids:
        cursor.execute("SELECT filename FROM ocr_results WHERE id = ?", (fid,))
        row = cursor.fetchone()
        if row:
            filepath = STORAGE_DIR / row[0]
            if filepath.exists():
                filepath.unlink()
        cursor.execute("DELETE FROM ocr_results WHERE id = ?", (fid,))
    conn.commit()
    return RedirectResponse(url="/admin", status_code=303)

# === Static ===
app.mount("/images", StaticFiles(directory=STORAGE_DIR), name="images")
