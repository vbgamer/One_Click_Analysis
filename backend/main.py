from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uuid
import os
import shutil
import json
from pathlib import Path
import models, schemas, auth, database
from database import engine

# ML Imports
from ml import etl, eda, automl, viz, reporting, insights

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="One Click Analysis API")

# CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount Static Files
# Mount charts and reports so they can be accessed via URL
os.makedirs("static/reports", exist_ok=True)
os.makedirs("static/charts", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Background Processing Task ---
def process_dataset_task(job_id: str, file_path: str, user_id: int, db: Session):
    # Separate session for background task to avoid threading issues
    # But since we pass 'db' from dependency, we should be careful. 
    # Better to create a new session or use the one provided if scoped correctly.
    # For simplicity, we'll try/except the logic and update status.
    
    try:
        # Update status to PROCESSING
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        job.status = models.JobStatus.PROCESSING
        db.commit()

        # 1. Load & Clean
        df = etl.load_data(file_path)
        df = etl.clean_data(df)
        
        # 2. EDA (YData Profiling)
        # We start it but save to a temp path first
        report_filename = f"report_{job_id}.html"
        report_path = f"static/reports/{report_filename}"
        ydata_path = f"static/reports/{report_filename.replace('.html', '_profile.html')}"
        
        # This generates the _profile.html and returns enriched stats
        stats = eda.perform_eda(df, output_path=ydata_path)
        
        # 3. AutoML FIRST (no time budget — trains until convergence)
        #    Run before viz so feature importance is available for charts
        ml_results = automl.train_model(df)  # No time limit
        
        # 4. Visualization with enriched context
        charts_dir = f"static/charts/{job_id}"
        charts = viz.generate_charts(df, charts_dir, ml_results=ml_results, eda_stats=stats)
        
        # Save Metadata for Report Builder
        metadata_path = f"{charts_dir}/metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(charts, f)
        
        # 5. AI Insights with full statistical context
        ai_text = insights.generate_insights(
            summary_stats=stats,
            target_col=ml_results.get('target_col'),
            model_metrics=ml_results.get('metrics', {})
        )
        
        # 6. Generate Final Report (Merge YData + AutoML)
        reporting.generate_html_report(
            metadata={"filename": job.filename},
            eda_stats=stats,
            ml_results=ml_results,
            charts=charts,
            output_path=report_path,
            job_id=job_id,
            insights=ai_text
        )
        
        # 7. Save Report to DB
        new_report = models.Report(
            id=str(uuid.uuid4()),
            job_id=job_id,
            user_id=user_id,
            report_html_url=f"/static/reports/{report_filename}"
        )
        db.add(new_report)
        
        # Update Job Status
        job.status = models.JobStatus.DONE
        job.report_url = new_report.report_html_url
        db.commit()
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"Error processing job {job_id}: {e}")
        with open("backend_error.log", "w") as f:
            f.write(error_msg)
        
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        job.status = models.JobStatus.FAILED
        db.commit()

# --- Auth Endpoints ---
@app.post("/auth/signup", response_model=schemas.User)
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

# --- Core App Endpoints ---
@app.post("/upload", response_model=schemas.Job)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Create Job
    job_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    save_path = f"static/uploads/{job_id}{file_ext}"
    
    # Save file
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    new_job = models.Job(
        id=job_id,
        user_id=current_user.id,
        filename=file.filename,
        status=models.JobStatus.UPLOADED
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Start Background Task
    background_tasks.add_task(process_dataset_task, job_id, save_path, current_user.id, db)
    
    return new_job

@app.get("/status/{job_id}", response_model=schemas.Job)
def get_status(job_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return job

@app.get("/my-reports", response_model=list[schemas.Job])
def get_my_reports(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    jobs = db.query(models.Job).filter(models.Job.user_id == current_user.id).order_by(models.Job.created_at.desc()).all()
    return jobs

@app.delete("/reports/{job_id}", status_code=200)
def delete_report(job_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    # 1. Check if job exists & ownership
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this report")

    # 2. Delete files
    # Uploaded file
    if job.filename:
        file_ext = os.path.splitext(job.filename)[1]
        upload_path = f"static/uploads/{job_id}{file_ext}"
        if os.path.exists(upload_path):
            os.remove(upload_path)
    
    # Report HTMLs
    report_path = f"static/reports/report_{job_id}.html"
    profile_path = f"static/reports/report_{job_id}_profile.html"
    if os.path.exists(report_path):
        os.remove(report_path)
    if os.path.exists(profile_path):
        os.remove(profile_path)
        
    # Charts Directory
    charts_dir = f"static/charts/{job_id}"
    if os.path.exists(charts_dir):
        shutil.rmtree(charts_dir)
        
    # 3. Delete DB Records
    # Cascade delete should handle Report if configured, but let's be safe
    db.query(models.Report).filter(models.Report.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    
    return {"message": "Report deleted successfully"}

@app.post("/chat")
def chat_with_data(request: schemas.ChatRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    # 1. Authorization & Job Retrieval
    job = db.query(models.Job).filter(models.Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # 2. Convert raw file path
    # Filename stored in DB, but we need full path. 
    # Logic from upload: static/uploads/{job_id}{ext}
    if not job.filename:
         raise HTTPException(status_code=400, detail="No file associated with this job")
         
    file_ext = os.path.splitext(job.filename)[1]
    file_path = f"static/uploads/{job.id}{file_ext}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Data file not found on server")
        
    # 3. Load Data & Prompt
    try:
        # Load and quick clean (lightweight version of Etl)
        df = etl.load_data(file_path) 
        # We don't run full clean_data to save time/mem, assuming initial upload was clean enough or robustness in insights
        # However, for consistency, let's run clean_data since it handles col names
        df = etl.clean_data(df) 
        
        reply = insights.ask_dataset_question(df, request.message)
        return {"reply": reply}
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat query")


@app.get("/")
def read_root():
    return {"message": "One Click Analysis API is running"}

@app.get("/reports/{job_id}/charts")
def get_job_charts(job_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    # Verify ownership
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    metadata_path = f"static/charts/{job_id}/metadata.json"
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Charts not found. Analysis might be incomplete.")
        
    with open(metadata_path, 'r') as f:
        return json.load(f)

@app.post("/reports/{job_id}/custom")
def generate_custom_report(job_id: str, request: schemas.CustomReportRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    # 1. Verify ownership
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 2. Prepare paths
    report_filename = f"custom_report_{job_id}_{uuid.uuid4().hex[:6]}.html"
    report_path = f"static/reports/{report_filename}"
    
    try:
        metadata_path = f"static/charts/{job_id}/metadata.json"
        if not os.path.exists(metadata_path):
             raise HTTPException(status_code=404, detail="Chart metadata not found. Please re-run analysis.")
             
        with open(metadata_path, 'r') as f:
            try:
                all_charts = json.load(f)
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="Metadata corrupted. Please re-run analysis.")
        
        # Custom Metadata
        bg_color = request.metadata.get("backgroundColor", "#f3f4f6")
        item_titles = request.metadata.get("itemTitles", {})

        # Flatten charts for easy lookup
        chart_lookup = {}
        for cat, items in all_charts.items():
            for item in items:
                chart_lookup[item['path']] = item

        # Filter and Organize Charts based on Layout
        dashboard_list = []
        
        # Sort layout by Y then X to maintain visual order in linear HTML
        sorted_layout = sorted(request.layout, key=lambda l: (l.y, l.x))
        
        for layout_item in sorted_layout:
             # 'i' in layout item is the chart path
             chart_path = layout_item.i
             if chart_path in chart_lookup:
                 chart_meta = chart_lookup[chart_path].copy()
                 # Overwrite title if renamed
                 if chart_path in item_titles:
                     chart_meta['title'] = item_titles[chart_path]
                 dashboard_list.append(chart_meta)
        
        # If no layout provided (fallback), use selected_charts list
        if not dashboard_list and request.selected_charts:
             for path in request.selected_charts:
                 if path in chart_lookup:
                     dashboard_list.append(chart_lookup[path])

        # Group into a single "Custom Dashboard" category for the report generator
        filtered_charts = {"Custom Dashboard": dashboard_list}
            
        reporting.generate_html_report(
            metadata={
                "filename": f"Custom Report: {request.title}",
                "backgroundColor": bg_color 
            },
            eda_stats={}, 
            ml_results={"target_col": "Custom View"},
            charts=filtered_charts,
            output_path=report_path,
            job_id=job_id,
            insights=f"Custom report generated by user: {current_user.name}"
        )
        
        return {"report_url": f"/static/reports/{report_filename}"}

    except Exception as e:
        print(f"Custom Gen Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/{job_id}/ai-layout")
def recommend_layout(job_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    """
    AI Agent that analyzes available charts and recommends a professional dashboard layout.
    """
    # 1. Load Metadata
    metadata_path = f"static/charts/{job_id}/metadata.json"
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Charts not found")
        
    with open(metadata_path, 'r') as f:
        all_charts = json.load(f)
        
    layout = []
    y_cursor = 0
    
    # helper to add item
    def add_item(path, w, h):
        nonlocal y_cursor
        item = {
            "i": path,
            "x": 0, # Simplified: Just stack them or put side-by-side logic below
            "y": y_cursor,
            "w": w,
            "h": h
        }
        layout.append(item)
        # Advance cursor logic (simple stacking for now, can be improved)
        # For a grid, we want 2 per row usually
        return item

    # flatten
    available_items = []
    for cat, items in all_charts.items():
        for item in items:
            if item['path']: # Skip text-only placeholders if needed
                item['category'] = cat
                available_items.append(item)
                
    # Logic: 
    # Row 1: KPI Cards (Small, width 2 or 3)
    # Row 2: Top Trends (Line/Area) (Width 6)
    # Row 3: Comparisons (Bar) (Width 6)
    
    # 1. KPIs
    kpis = [x for x in available_items if "KPI" in x['category']]
    for idx, kpi in enumerate(kpis):
        # 4 KPIs per row (Width 3 each, total 12)
        row_pos = idx % 4
        if row_pos == 0 and idx > 0: 
            y_cursor += 2
            
        layout.append({
            "i": kpi['path'],
            "x": row_pos * 3,
            "y": y_cursor,
            "w": 3,
            "h": 2
        })
        
    if kpis: y_cursor += 2
    
    # 2. Key Charts (Distributions & Trends)
    other_charts = [x for x in available_items if "KPI" not in x['category']]
    # Limit to top 6 relevant charts to avoid clutter
    priority_charts = other_charts[:6]
    
    for idx, chart in enumerate(priority_charts):
        # 2 per row (Width 6 each)
        row_pos = idx % 2
        if row_pos == 0 and idx > 0:
            y_cursor += 4 # Height of charts
            
        layout.append({
            "i": chart['path'],
            "x": row_pos * 6,
            "y": y_cursor,
            "w": 6,
            "h": 4
        })

    return {"layout": layout}


