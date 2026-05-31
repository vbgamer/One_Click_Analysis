from fastapi import (
    FastAPI, Depends, HTTPException, status, UploadFile, File,
    BackgroundTasks, WebSocket, WebSocketDisconnect
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uuid
import os
import shutil
import json
import traceback
import datetime
from pathlib import Path

import models, schemas, auth, database
from database import engine
from routers import admin as admin_router

# ── Legacy ML Imports (kept for backward compatibility) ───────────────────────
try:
    from ml import etl, eda, viz, reporting, insights
    try:
        from ml import automl
    except ImportError:
        automl = None
    LEGACY_ML_AVAILABLE = True
except Exception:
    LEGACY_ML_AVAILABLE = False
    etl = eda = automl = viz = reporting = insights = None

# ── New AI Pipeline ───────────────────────────────────────────────────────────
try:
    from ml import pipeline as ai_pipeline
    AI_PIPELINE_AVAILABLE = True
except Exception:
    AI_PIPELINE_AVAILABLE = False
    ai_pipeline = None

# ── DB Tables ─────────────────────────────────────────────────────────────────
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="One Click Analysis — AI Expense Intelligence API",
    description="AI-native expense analytics with forecasting, anomaly detection, and conversational AI.",
    version="2.0.0"
)

# Register admin router
app.include_router(admin_router.router)

# ── Seed Default Users on Startup ─────────────────────────────────────────────
@app.on_event("startup")
def seed_users():
    """Create default admin + test users if they don't already exist."""
    db = next(database.get_db())
    seed_data = [
        {"email": "admin@admin.com",         "name": "Administrator", "password": "Admin@2003", "role": "admin", "credits": 99999999},
        {"email": "customer1@customer.com",   "name": "Customer One",  "password": "ved@123",    "role": "user",  "credits": 99999999},
        {"email": "customer2@customer.com",   "name": "Customer Two",  "password": "ved@123",    "role": "user",  "credits": 100},
    ]
    for s in seed_data:
        existing = db.query(models.User).filter(models.User.email == s["email"]).first()
        if not existing:
            db.add(models.User(
                email=s["email"],
                name=s["name"],
                hashed_password=auth.get_password_hash(s["password"]),
                role=s["role"],
                credits=s["credits"],
            ))
    db.commit()
    db.close()

    # Ensure AI results dir exists
    os.makedirs("static/ai_results", exist_ok=True)


# ── CORS ──────────────────────────────────────────────────────────────────────
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://192.168.0.103:5173",
    "http://192.168.0.103:8000",
]
if os.getenv("FRONTEND_URL"):
    origins.append(os.getenv("FRONTEND_URL").rstrip("/"))
if os.getenv("ALLOWED_ORIGINS"):
    origins.extend([o.strip().rstrip("/") for o in os.getenv("ALLOWED_ORIGINS").split(",")])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.(vercel|netlify)\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Files ──────────────────────────────────────────────────────────────
os.makedirs("static/reports", exist_ok=True)
os.makedirs("static/charts", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/ai_results", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY BACKGROUND PROCESSING (kept for old-style HTML reports)
# ─────────────────────────────────────────────────────────────────────────────
def process_dataset_task(job_id: str, file_path: str, user_id: int, db: Session):
    """Original processing pipeline — runs EDA + AutoML + HTML report."""
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        job.status = models.JobStatus.PROCESSING
        db.commit()

        df = etl.load_data(file_path)
        df = etl.clean_data(df)

        report_filename = f"report_{job_id}.html"
        report_path = f"static/reports/{report_filename}"
        ydata_path = f"static/reports/{report_filename.replace('.html', '_profile.html')}"

        stats = eda.perform_eda(df, output_path=ydata_path)

        if automl:
            ml_results = automl.train_model(df)
        else:
            ml_results = {"target_col": "unknown", "metrics": {}}

        charts_dir = f"static/charts/{job_id}"
        try:
            charts = viz.generate_charts(df, charts_dir, ml_results=ml_results, eda_stats=stats)
        except Exception:
            charts = {}

        metadata_path = f"{charts_dir}/metadata.json"
        os.makedirs(charts_dir, exist_ok=True)
        with open(metadata_path, "w") as f:
            json.dump(charts, f)

        ai_text = insights.generate_insights(
            summary_stats=stats,
            target_col=ml_results.get("target_col"),
            model_metrics=ml_results.get("metrics", {})
        )

        reporting.generate_html_report(
            metadata={"filename": job.filename},
            eda_stats=stats,
            ml_results=ml_results,
            charts=charts,
            output_path=report_path,
            job_id=job_id,
            insights=ai_text,
        )

        new_report = models.Report(
            id=str(uuid.uuid4()),
            job_id=job_id,
            user_id=user_id,
            report_html_url=f"/static/reports/{report_filename}",
        )
        db.add(new_report)

        job.status = models.JobStatus.DONE
        job.report_url = new_report.report_html_url
        db.commit()

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"[ERROR] Legacy pipeline for job {job_id}: {e}")
        with open("backend_error.log", "w") as f:
            f.write(error_msg)
        try:
            job = db.query(models.Job).filter(models.Job.id == job_id).first()
            if job:
                job.status = models.JobStatus.FAILED
                db.commit()
        except Exception:
            pass


def run_ai_pipeline_task(job_id: str, file_path: str, db: Session):
    """New AI intelligence pipeline — runs in background after upload."""
    if not AI_PIPELINE_AVAILABLE:
        return
    try:
        ai_rec = db.query(models.AIResult).filter(models.AIResult.job_id == job_id).first()
        if not ai_rec:
            ai_rec = models.AIResult(id=str(uuid.uuid4()), job_id=job_id)
            db.add(ai_rec)
        ai_rec.status = "running"
        db.commit()

        import pandas as pd
        df = pd.read_csv(file_path) if file_path.endswith(".csv") else None
        if df is None:
            try:
                df = pd.read_excel(file_path)
            except Exception:
                pass

        if df is None or len(df) == 0:
            raise ValueError("Could not load dataframe")

        results = ai_pipeline.run_full_analysis(df, job_id)

        # ── Normalize key names so frontend always gets consistent fields ──
        # Pipeline emits `quality_score` and `confidence`, but DB+API use the longer names
        if "data_quality_score" not in results:
            qs = results.get("quality_score", {})
            if isinstance(qs, dict):
                results["data_quality_score"] = qs.get("overall", None)
            else:
                results["data_quality_score"] = qs

        if "confidence_score" not in results:
            cf = results.get("confidence", {})
            if isinstance(cf, dict):
                results["confidence_score"] = cf.get("overall", None)
            else:
                results["confidence_score"] = cf

        # ── Inject a summary block the Intelligence.jsx KPI cards expect ──
        if "summary" not in results:
            try:
                import pandas as _pd
                amount_col = results.get("schema", {}).get("amount_col")
                total_amount = None
                if amount_col and amount_col in df.columns:
                    total_amount = float(_pd.to_numeric(df[amount_col], errors="coerce").sum())
                results["summary"] = {
                    "rows": len(df),
                    "cols": df.shape[1],
                    "total_amount": total_amount,
                }
            except Exception:
                results["summary"] = {"rows": len(df), "cols": df.shape[1], "total_amount": None}

        # ── Always regenerate charts with current plotly install ──
        try:
            from ml import viz as _viz
            schema = results.get("schema", {})
            results["charts"] = _viz.generate_all_charts(df, schema, results)
            good = sum(1 for v in results["charts"].values() if len(v.get("data", [])) > 0)
            print(f"[pipeline] Charts generated: {good}/{len(results['charts'])} with data")
        except Exception as _ve:
            print(f"[WARN] Chart generation failed: {_ve}")
            if "charts" not in results:
                results["charts"] = {}

        ai_rec.status = "done"
        ai_rec.results_json = json.dumps(results)
        ai_rec.schema_json = json.dumps(results.get("schema", {}))
        ai_rec.data_quality_score = results.get("data_quality_score")
        ai_rec.confidence_score = results.get("confidence_score")
        ai_rec.anomaly_count = results.get("anomalies", {}).get("anomaly_count", 0)
        ai_rec.recommendation_count = len(results.get("recommendations") or [])
        ai_rec.completed_at = datetime.datetime.utcnow()
        db.commit()

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"[ERROR] AI pipeline for job {job_id}: {e}")
        try:
            ai_rec = db.query(models.AIResult).filter(models.AIResult.job_id == job_id).first()
            if ai_rec:
                ai_rec.status = "failed"
                ai_rec.error_message = str(e)[:1000]
                db.commit()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# AUTH ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/auth/signup", response_model=schemas.User)
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(
        email=user.email,
        name=user.name,
        hashed_password=auth.get_password_hash(user.password),
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


# ─────────────────────────────────────────────────────────────────────────────
# CREDIT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/credits/request", response_model=schemas.CreditRequestOut)
def request_credits(
    payload: schemas.CreditRequestCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    new_req = models.CreditRequest(
        user_id=current_user.id,
        amount_requested=payload.amount_requested,
        note=payload.note,
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return new_req


# ─────────────────────────────────────────────────────────────────────────────
# CORE UPLOAD + JOBS
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/upload", response_model=schemas.Job)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    ANALYSIS_COST = 100
    if current_user.credits != -1 and current_user.credits < ANALYSIS_COST:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {ANALYSIS_COST}, have {current_user.credits}.",
        )

    job_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    save_path = f"static/uploads/{job_id}{file_ext}"

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if current_user.credits != -1:
        current_user.credits -= ANALYSIS_COST
        db.commit()

    new_job = models.Job(
        id=job_id,
        user_id=current_user.id,
        filename=file.filename,
        status=models.JobStatus.UPLOADED,
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Launch both pipelines in background
    if LEGACY_ML_AVAILABLE:
        background_tasks.add_task(process_dataset_task, job_id, save_path, current_user.id, db)
    if AI_PIPELINE_AVAILABLE:
        background_tasks.add_task(run_ai_pipeline_task, job_id, save_path, db)

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
    return db.query(models.Job).filter(models.Job.user_id == current_user.id).order_by(models.Job.created_at.desc()).all()


@app.delete("/reports/{job_id}", status_code=200)
def delete_report(job_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if job.filename:
        ext = os.path.splitext(job.filename)[1]
        for path in [
            f"static/uploads/{job_id}{ext}",
            f"static/reports/report_{job_id}.html",
            f"static/reports/report_{job_id}_profile.html",
            f"static/ai_results/{job_id}.json",
        ]:
            if os.path.exists(path):
                os.remove(path)

    charts_dir = f"static/charts/{job_id}"
    if os.path.exists(charts_dir):
        shutil.rmtree(charts_dir)

    db.query(models.Report).filter(models.Report.job_id == job_id).delete()
    db.query(models.AIResult).filter(models.AIResult.job_id == job_id).delete()
    db.query(models.ConversationMessage).filter(models.ConversationMessage.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    return {"message": "Report deleted successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY CHAT
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/chat")
def chat_with_data(request: schemas.ChatRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    job = db.query(models.Job).filter(models.Job.id == request.job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not job.filename:
        raise HTTPException(status_code=400, detail="No file associated with this job")

    file_ext = os.path.splitext(job.filename)[1]
    file_path = f"static/uploads/{job.id}{file_ext}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Data file not found on server")

    try:
        df = etl.load_data(file_path)
        df = etl.clean_data(df)
        reply = insights.ask_dataset_question(df, request.message)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY REPORT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/reports/{job_id}/charts")
def get_job_charts(job_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    metadata_path = f"static/charts/{job_id}/metadata.json"
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Charts not found.")
    with open(metadata_path, "r") as f:
        return json.load(f)


@app.post("/reports/{job_id}/custom")
def generate_custom_report(job_id: str, request: schemas.CustomReportRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    report_filename = f"custom_report_{job_id}_{uuid.uuid4().hex[:6]}.html"
    report_path = f"static/reports/{report_filename}"

    try:
        metadata_path = f"static/charts/{job_id}/metadata.json"
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Chart metadata not found.")
        with open(metadata_path, "r") as f:
            all_charts = json.load(f)

        chart_lookup = {}
        for cat, items in all_charts.items():
            for item in items:
                chart_lookup[item["path"]] = item

        sorted_layout = sorted(request.layout, key=lambda l: (l.y, l.x))
        dashboard_list = []
        for layout_item in sorted_layout:
            if layout_item.i in chart_lookup:
                meta = chart_lookup[layout_item.i].copy()
                if layout_item.i in request.metadata.get("itemTitles", {}):
                    meta["title"] = request.metadata["itemTitles"][layout_item.i]
                dashboard_list.append(meta)

        if not dashboard_list and request.selected_charts:
            for path in request.selected_charts:
                if path in chart_lookup:
                    dashboard_list.append(chart_lookup[path])

        reporting.generate_html_report(
            metadata={"filename": f"Custom Report: {request.title}", "backgroundColor": request.metadata.get("backgroundColor", "#f3f4f6")},
            eda_stats={},
            ml_results={"target_col": "Custom View"},
            charts={"Custom Dashboard": dashboard_list},
            output_path=report_path,
            job_id=job_id,
            insights=f"Custom report generated by user: {current_user.name}",
        )
        return {"report_url": f"/static/reports/{report_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/{job_id}/ai-layout")
def recommend_layout(job_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    metadata_path = f"static/charts/{job_id}/metadata.json"
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Charts not found")
    with open(metadata_path, "r") as f:
        all_charts = json.load(f)

    layout, y_cursor = [], 0
    available_items = [
        {**item, "category": cat}
        for cat, items in all_charts.items()
        for item in items if item.get("path")
    ]
    kpis = [x for x in available_items if "KPI" in x["category"]]
    for idx, kpi in enumerate(kpis):
        row_pos = idx % 4
        if row_pos == 0 and idx > 0:
            y_cursor += 2
        layout.append({"i": kpi["path"], "x": row_pos * 3, "y": y_cursor, "w": 3, "h": 2})
    if kpis:
        y_cursor += 2
    for idx, chart in enumerate([x for x in available_items if "KPI" not in x["category"]][:6]):
        row_pos = idx % 2
        if row_pos == 0 and idx > 0:
            y_cursor += 4
        layout.append({"i": chart["path"], "x": row_pos * 6, "y": y_cursor, "w": 6, "h": 4})
    return {"layout": layout}


# ─────────────────────────────────────────────────────────────────────────────
# ★ NEW: AI INTELLIGENCE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

def _get_ai_result_json(job_id: str, user_id: int, db: Session) -> dict:
    """Helper: load AI result for a job, verify ownership."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Try DB first
    ai_rec = db.query(models.AIResult).filter(models.AIResult.job_id == job_id).first()
    if ai_rec and ai_rec.results_json:
        return json.loads(ai_rec.results_json)

    # Try file cache
    result_path = f"static/ai_results/{job_id}.json"
    if os.path.exists(result_path):
        with open(result_path, "r") as f:
            return json.load(f)

    raise HTTPException(status_code=404, detail="AI analysis not found. Run /analyze/{job_id}/run first.")


@app.post("/analyze/{job_id}/run")
def run_ai_analysis(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Trigger the full AI intelligence pipeline for a job."""
    if not AI_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI pipeline not available. Run: python manage.py runserver")

    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    file_ext = os.path.splitext(job.filename)[1]
    file_path = f"static/uploads/{job_id}{file_ext}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Source file not found. Re-upload to analyze.")

    # Create/reset AI result record
    ai_rec = db.query(models.AIResult).filter(models.AIResult.job_id == job_id).first()
    if not ai_rec:
        ai_rec = models.AIResult(id=str(uuid.uuid4()), job_id=job_id)
        db.add(ai_rec)
    ai_rec.status = "pending"
    ai_rec.error_message = None
    db.commit()

    background_tasks.add_task(run_ai_pipeline_task, job_id, file_path, db)
    return {"message": "AI analysis started", "job_id": job_id, "status": "pending"}


@app.get("/analyze/{job_id}/status")
def get_ai_status(
    job_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Check the status of an AI analysis."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    ai_rec = db.query(models.AIResult).filter(models.AIResult.job_id == job_id).first()
    if not ai_rec:
        return {"status": "not_started", "job_id": job_id}

    return {
        "status": ai_rec.status,
        "job_id": job_id,
        "data_quality_score": ai_rec.data_quality_score,
        "confidence_score": ai_rec.confidence_score,
        "anomaly_count": ai_rec.anomaly_count,
        "recommendation_count": ai_rec.recommendation_count,
        "error_message": ai_rec.error_message,
        "completed_at": ai_rec.completed_at.isoformat() if ai_rec.completed_at else None,
    }


@app.get("/analyze/{job_id}/results")
def get_full_ai_results(
    job_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get the full structured AI analysis results."""
    return _get_ai_result_json(job_id, current_user.id, db)


@app.get("/analyze/{job_id}/forecast")
def get_forecast(
    job_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get forecasting results (time-series predictions)."""
    results = _get_ai_result_json(job_id, current_user.id, db)
    return {
        "forecast": results.get("forecast", {}),
        "category_forecast": results.get("category_forecast", {}),
        "burn_rate": results.get("burn_rate", {}),
    }


@app.get("/analyze/{job_id}/anomalies")
def get_anomalies(
    job_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get detected anomalies and behavioral outliers."""
    results = _get_ai_result_json(job_id, current_user.id, db)
    return {
        "anomalies": results.get("anomalies", {}),
        "behavioral_anomalies": results.get("behavioral_anomalies", {}),
    }


@app.get("/analyze/{job_id}/recommendations")
def get_recommendations(
    job_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get AI-generated recommendations with explanations."""
    results = _get_ai_result_json(job_id, current_user.id, db)
    return {
        "recommendations": results.get("recommendations", []),
        "optimization_score": results.get("optimization_score", {}),
    }


@app.get("/analyze/{job_id}/settlement")
def get_settlement(
    job_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get settlement optimization and payer network."""
    results = _get_ai_result_json(job_id, current_user.id, db)
    return {
        "settlement": results.get("settlement", {}),
        "payer_network": results.get("payer_network", {}),
        "fairness": results.get("fairness", {}),
    }


@app.get("/analyze/{job_id}/insights")
def get_explainability(
    job_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get explainability data — confidence scores, SHAP, model card."""
    results = _get_ai_result_json(job_id, current_user.id, db)
    return {
        "confidence_score": results.get("confidence_score"),
        "data_quality_score": results.get("data_quality_score"),
        "schema": results.get("schema", {}),
        "entity_changes": results.get("entity_changes", {}),
        "leakage_warnings": results.get("leakage_warnings", []),
    }


@app.get("/analyze/{job_id}/charts")
def get_ai_charts(
    job_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get all Plotly chart JSON objects."""
    results = _get_ai_result_json(job_id, current_user.id, db)
    return results.get("charts", {})


@app.post("/analyze/{job_id}/ask")
def ask_ai_question(
    job_id: str,
    request: schemas.AIQueryRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Conversational AI — ask a natural language question about the data."""
    if not AI_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI pipeline not available.")

    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        results = _get_ai_result_json(job_id, current_user.id, db)
    except HTTPException:
        results = {}

    file_ext = os.path.splitext(job.filename)[1]
    file_path = f"static/uploads/{job_id}{file_ext}"

    try:
        import pandas as pd
        df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)
        schema = results.get("schema", {})

        answer_data = ai_pipeline.run_analytical_query(
            job_id=job_id,
            question=request.question,
            df=df,
            schema=schema,
            conversation_history=request.conversation_history,
        )

        # Persist message to DB
        db.add(models.ConversationMessage(
            job_id=job_id, role="user", content=request.question,
        ))
        db.add(models.ConversationMessage(
            job_id=job_id, role="assistant",
            content=answer_data.get("answer", ""),
            intent=answer_data.get("intent"),
            confidence=answer_data.get("confidence"),
        ))
        db.commit()

        return answer_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/analyze/{job_id}/conversation")
def get_conversation_history(
    job_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
):
    """Get conversational history for a job."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    messages = db.query(models.ConversationMessage).filter(
        models.ConversationMessage.job_id == job_id
    ).order_by(models.ConversationMessage.created_at).all()
    return [
        {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in messages
    ]


# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKET: Real-time conversational AI
# ─────────────────────────────────────────────────────────────────────────────
@app.websocket("/ws/chat/{job_id}")
async def websocket_chat(websocket: WebSocket, job_id: str, db: Session = Depends(database.get_db)):
    """WebSocket endpoint for real-time AI chat."""
    await websocket.accept()
    conversation_history = []

    # Pre-load df and schema for this job session
    _ws_df = None
    _ws_schema = {}
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if job and job.filename:
            import pandas as pd
            file_ext = os.path.splitext(job.filename)[1]
            file_path = f"static/uploads/{job_id}{file_ext}"
            if os.path.exists(file_path):
                _ws_df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)
            result_path = f"static/ai_results/{job_id}.json"
            if os.path.exists(result_path):
                import json as _json
                with open(result_path) as f:
                    _ws_schema = _json.load(f).get("schema", {})
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_json()
            question = data.get("message", "")
            if not question:
                continue

            conversation_history.append({"role": "user", "content": question})

            try:
                if AI_PIPELINE_AVAILABLE and _ws_df is not None:
                    answer_data = ai_pipeline.run_analytical_query(
                        job_id=job_id,
                        question=question,
                        df=_ws_df,
                        schema=_ws_schema,
                        conversation_history=conversation_history[-10:],
                    )
                    answer = answer_data.get("answer", "I couldn't process that question.")
                else:
                    answer = "AI pipeline is not available. Please ensure all dependencies are installed."

                conversation_history.append({"role": "assistant", "content": answer})
                await websocket.send_json({"answer": answer, "status": "ok"})

            except Exception as e:
                await websocket.send_json({"answer": f"Error: {str(e)}", "status": "error"})

    except WebSocketDisconnect:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# ROOT + FRONTEND HOSTING
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {
        "message": "One Click Analysis — AI Expense Intelligence API v2.0",
        "ai_pipeline": AI_PIPELINE_AVAILABLE,
        "legacy_ml": LEGACY_ML_AVAILABLE,
    }


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
frontend_assets = frontend_dist / "assets"

if frontend_dist.exists():
    if frontend_assets.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_assets)), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        requested = frontend_dist / full_path
        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(frontend_dist / "index.html")
