
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os, uuid, shutil, tempfile, traceback
from pathlib import Path
from agent import process_file, get_status, get_report_path

app = FastAPI(title="AI Backend Prototype", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

jobs = {}

@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{job_id}_{file.filename}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # launch background processing
    jobs[job_id] = {"status": "queued", "filename": str(dest)}
    background_tasks.add_task(_process, job_id, str(dest))
    return {"job_id": job_id, "message": "File received. Processing started."}

def _process(job_id: str, path: str):
    try:
        jobs[job_id]["status"] = "processing"
        report_path = process_file(path, job_id=job_id)
        jobs[job_id]["status"] = "done"
        jobs[job_id]["report"] = report_path
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = traceback.format_exc()

@app.get("/status/{job_id}")
def status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.get("/report/{job_id}", response_class=HTMLResponse)
def get_report(job_id: str):
    info = jobs.get(job_id)
    if not info:
        raise HTTPException(status_code=404, detail="Job not found")
    if info.get("status") != "done":
        raise HTTPException(status_code=400, detail="Report not ready")
    report_path = info.get("report")
    if not report_path or not Path(report_path).exists():
        raise HTTPException(status_code=500, detail="Report missing")
    return HTMLResponse(content=open(report_path, "r", encoding="utf-8").read())

@app.get("/download/{job_id}")
def download_report(job_id: str):
    info = jobs.get(job_id)
    if not info:
        raise HTTPException(status_code=404, detail="Job not found")
    report_path = info.get("report")
    if not report_path or not Path(report_path).exists():
        raise HTTPException(status_code=400, detail="Report not ready")
    return FileResponse(report_path, media_type="text/html", filename=Path(report_path).name)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
