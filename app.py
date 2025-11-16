from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import shutil
import uuid
from pathlib import Path
import traceback

from agent import process_file

app = FastAPI(title="One Click Analysis", version="1.0")

# Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload & processed folders
UPLOAD_DIR = Path("uploads"); UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR = Path("processed"); PROCESSED_DIR.mkdir(exist_ok=True)

# Serve processed reports and images
app.mount("/processed", StaticFiles(directory="processed"), name="processed")

jobs = {}

# ------------------------------ FRONTEND PAGE -----------------------------

@app.get("/", response_class=HTMLResponse)
def frontend():
    return """
    <html>
    <head>
        <title>One Click Analysis</title>
        <style>
            body { font-family: Arial; padding: 40px; background: #f4f4f4; }
            .card { background: white; padding: 30px; border-radius: 12px; width: 420px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            button { padding: 12px 20px; background: black; color: white; 
                     cursor: pointer; border-radius: 8px; border: none; }
        </style>
    </head>
    <body>
        <h1>📊 One Click Analysis</h1>
        <p>Upload your dataset and get instant AI-generated reports.</p>
        <div class="card">
            <form method="post" action="/upload" enctype="multipart/form-data">
                <input type="file" name="file" required><br><br>
                <button type="submit">Generate Report</button>
            </form>
        </div>
    </body>
    </html>
    """


# ------------------------------ UPLOAD & PROCESS -----------------------------

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{job_id}_{file.filename}"

    # Save file
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Process instantly (not background for simplicity)
    try:
        report_path = process_file(str(dest), job_id=job_id)
    except Exception as e:
        return HTMLResponse(f"<h3>Error: {traceback.format_exc()}</h3>")

    # Show link to report
    return HTMLResponse(f"""
        <h2>✔ Report generated!</h2>
        <p><a href="/processed/{job_id}/report.html" target="_blank">Click here to open your report</a></p>
        <br><a href="/">⬅ Back to Dashboard</a>
    """)


# ------------------------------ RUN SERVER -----------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
