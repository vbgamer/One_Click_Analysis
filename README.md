# 🚀 One Click Analysis - AI-Powered Data Analyst Dashboard

An advanced, full-stack data science platform that democratizes machine learning, exploratory data analysis, and business intelligence. By leveraging FastAPI, React, Supabase, and Multi-Agent AI (Microsoft AutoGen), this application transforms raw datasets into professional-grade analytical reports in seconds.

## 🌟 Key Features

- **Automated Exploratory Data Analysis (EDA):** Generates statistical profiles, outliner detection, and correlation matrices autonomously.
- **Analyst-Grade Visualizations:** Creates tailored top-10 charts, Pareto distributions, and time-series trend lines.
- **Fast Lightweight AutoML:** Utilizes FLAML to train and evaluate multiple predictive models (XGBoost, Random Forest, etc.) and provides instant ROC/AUC metrics.
- **Power-BI Style Report Builder:** A drag-and-drop, grid-based interface allowing users to arrange and publish custom dashboards from generated charts.
- **"Chat with Data" Interface:** Chat directly with your dataset using an integrated LLM to ask plain-English analytical questions.
- **Built-in Credits Economy & Admin Panel:** 
  - Tracks user usage via a Credit System (e.g., -100 credits per analysis).
  - Secure Admin Dashboard to monitor users, edit balances, and approve credit requests.
- **Supabase Cloud Database:** High-performance, production-ready PostgreSQL persistence using SQLAlchemy and session pooling.

---

## 🏗️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React, Vite, Framer Motion, Axios, React Router |
| **Backend API** | FastAPI, Uvicorn, Python, SQLAlchemy, Pydantic V2 |
| **Database** | Supabase (PostgreSQL) |
| **Machine Learning** | Pandas, Scikit-Learn, FLAML |
| **Visualization** | Matplotlib, Seaborn, YData Profiling |
| **Agentic AI** | Microsoft AutoGen, OpenRouter, HuggingFace |

---

## 🛠️ Quick Start & Setup

### 1. Database Configuration (Supabase)
This project uses **Supabase (PostgreSQL)**. 
1. Get your IPv4 Session Pooler URI from your Supabase Dashboard.
2. Create a `.env` file in the `backend/` directory:
```env
DATABASE_URL="postgresql://postgres.[project]:[password]@aws-0-region.pooler.supabase.com:5432/postgres"
JWT_SECRET_KEY="your-secret-key"
```

### 2. Backend Setup
The backend requires Python 3.10+.
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*Note: On the first boot, three test accounts are seeded into your database automatically:*
- `admin@admin.com` / `Admin@2003` (Admin Role, ∞ Credits)
- `customer1@customer.com` / `ved@123` (User Role, ∞ Credits)
- `customer2@customer.com` / `ved@123` (User Role, 100 Credits)

### 3. Frontend Setup
The frontend uses Vite.
```bash
cd frontend
npm install
npx vite --host
```
The application will be running at `http://localhost:5173`.

---

## 🌐 Production Deployment Architecture
- **Frontend:** Deployed to **Vercel**. Securely handles 402 out-of-credit responses globally.
- **Backend:** Designed to be deployed on a high-compute Python container service like **Render or Railway**.
- **Database:** Fully hosted managed PostgreSQL on **Supabase**.

---

*This project was developed to merge Data Science heavily with modern Web Architecture.*
