# macos_ocr_http_service.py

import os
import uuid
import shutil
import asyncio
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

# === CORS (if needed) ===
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
    from Foundation import NSURL, NSDictionary
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

    image_url = NSURL.fileURLWithPath_(image_path)
    src = Quartz.CGImageSourceCreateWithURL(image_url, None)
    if src is None:
        raise ValueError("Could not create image source")

    cgimage = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    if cgimage is None:
        raise ValueError("Could not create CGImage from source")

    request = VNRecognizeTextRequest.alloc().initWithCompletionHandler_(handler_fn)
    request.setRecognitionLanguages_(["zh-Hans", "zh-Hant", "en-US"])
    request.setRecognitionLevel_(1)

    handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cgimage, NSDictionary.dictionary())
    handler.performRequests_error_([request], None)

    return "\n".join(results_text)

# === Background OCR Task ===
async def process_image_async(file_id: str, image_path: Path):
    try:
        text = run_native_ocr(str(image_path))
        cursor.execute("UPDATE ocr_results SET text = ?, status = ? WHERE id = ?", (text, "done", file_id))
    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"[ERROR] OCR failed for {file_id}:\n{err_msg}")
        cursor.execute("UPDATE ocr_results SET text = ?, status = ? WHERE id = ?", (err_msg, "error", file_id))
    conn.commit()

# === API ===
@app.post("/upload")
async def upload_image(file: UploadFile):
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = STORAGE_DIR / filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    cursor.execute("INSERT INTO ocr_results (id, filename, status) VALUES (?, ?, ?)", (file_id, filename, "processing"))
    conn.commit()
    asyncio.create_task(process_image_async(file_id, file_path))
    return {"file_id": file_id}

@app.get("/status/{file_id}")
def check_status(file_id: str):
    cursor.execute("SELECT status FROM ocr_results WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    return {"file_id": file_id, "status": row[0] if row else "not_found"}

@app.get("/result/{file_id}")
def get_result(file_id: str):
    cursor.execute("SELECT text FROM ocr_results WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    return {"file_id": file_id, "text": row[0] if row else None}

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

