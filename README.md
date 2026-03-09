# 🚀 One Click Analysis

> **Automated AI Data Analyst SaaS**  
> Upload your dataset and get a professional, comprehensive data analysis report in seconds. Powered by State-of-the-Art AutoML and LLMs.

---

## 📖 About The Project

**One Click Analysis** is a full-stack SaaS application designed to democratize data science. It simplifies the complex pipeline of data cleaning, exploratory data analysis (EDA), and machine learning modeling into a single "drag-and-drop" action.

**Problem**: Data analysis requires coding skills (Python/Pandas) and time-consuming manual work.  
**Solution**: A "One Click" platform that accepts messy data and outputs a complete, actionable HTML report with insights.

### ✨ Key Features
*   **One-Click Pipeline**: From raw CSV/Excel to full report in < 30 seconds.
*   **Robust ETL**: automatically cleans data, handles missing values, and fixes schema errors.
*   **Deep EDA**: powered by **YData Profiling** for industry-standard statistical analysis.
*   **AutoML Engine**: uses **FLAML (by Microsoft)** to train multiple models (XGBoost, LightGBM, CatBoost) and find the best one automatically.
*   **AI Analyst**: integrates **Hugging Face** LLMs (Mistral-7B) to write executive summaries in plain English.
*   **Modern Dashboard**: Responsive React UI with Dark Mode support.
*   **Secure**: JWT Authentication and password hashing (PBKDF2).

---

## 🛠 Tech Stack

### Frontend
*   **Framework**: [React](https://reactjs.org/) (Vite)
*   **Styling**: Vanilla CSS with modern CSS Variables (Theming)
*   **Routing**: React Router DOM (Protected Routes)
*   **State/API**: Axios, LocalStorage for JWT

### Backend
*   **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance Python API)
*   **Database**: SQLite (Dev) / PostgreSQL (Ready), Managed via **SQLAlchemy**
*   **Auth**: OAuth2 with JWT Tokens & PBKDF2 Hashing
*   **Async Processing**: FastAPI BackgroundTasks

### 🤖 AI & Machine Learning Core
*   **Data Processing**: `Pandas`, `NumPy`
*   **Exploratory Analysis**: `ydata-profiling` (formerly pandas-profiling)
*   **AutoML**: `FLAML` (Fast and Lightweight AutoML)
*   **LLM Insights**: `huggingface_hub` Inference API
*   **Visualization**: `Matplotlib`, `Seaborn`

---

## 🔄 System Architecture & Workflow

1.  **User Upload**: User drags a CSV/Excel file to the Dashboard.
2.  **API Handling**: Backend accepts file, saves to `static/uploads`, and creates a `Job` record (Status: PENDING).
3.  **Background Processing**:
    *   **Step 1 (ETL)**: `etl.py` loads and cleans the data (imputation, deduplication).
    *   **Step 2 (EDA)**: `eda.py` generates a deep HTML profile using YData.
    *   **Step 3 (AutoML)**: `automl.py` uses FLAML to identify the target variable and train 5+ models to maximize accuracy/R2.
    *   **Step 4 (Insights)**: `insights.py` sends statistics to a Hugging Face LLM to generate text.
    *   **Step 5 (Reporting)**: `reporting.py` combines the YData HTML, AutoML metrics, and AI text into a final `report_{id}.html`.
4.  **Notification**: Frontend polls `/status/{id}` and updates UI to "DONE".
5.  **Delivery**: User views the interactive HTML report directly in the browser or downloads it.

---

## 🚀 Getting Started

### Prerequisites
*   Node.js (v18+)
*   Python (v3.9+)

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/one-click-analysis.git
    cd one-click-analysis
    ```

2.  **Backend Setup**
    ```bash
    cd backend
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    # source venv/bin/activate
    
    pip install -r requirements.txt
    ```

3.  **Frontend Setup**
    ```bash
    cd ../frontend
    npm install
    ```

### Running the App

1.  **Start Backend** (Terminal 1)
    ```bash
    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

2.  **Start Frontend** (Terminal 2)
    ```bash
    cd frontend
    npm run dev
    ```

3.  **Access App**
    *   Frontend: `http://localhost:5173`
    *   API Docs: `http://localhost:8000/docs`

---

## 📁 Project Structure

```
one-click-analysis/
├── backend/
│   ├── ml/                 # The "Brain" of the operation
│   │   ├── etl.py          # Data Cleaning
│   │   ├── eda.py          # YData Profiling Wrapper
│   │   ├── automl.py       # FLAML Integration
│   │   ├── insights.py     # LLM Integration
│   │   └── reporting.py    # HTML Generation
│   ├── main.py             # API Entry Point
│   ├── models.py           # Database Schemas
│   └── auth.py             # Security Logic
│
└── frontend/
    ├── src/
    │   ├── components/     # Reusable UI (Layout, Loader)
    │   ├── pages/          # Dashboard, Login, ReportView
    │   └── styles/         # CSS design system
    └── vite.config.js      # Proxy configuration
```

---

## 🤝 Contributing
1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request
