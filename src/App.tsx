// App.jsx
import React, { useState } from "react";
import './styles.css';

// Removed SAMPLE FILE PATH — user can now upload ANY CSV file

export default function App(){
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reportUrl, setReportUrl] = useState("");
  const [message, setMessage] = useState("");

  async function uploadFile(inputFile){
    setLoading(true);
    setMessage('Uploading...');
    try{
      const fd = new FormData();
      fd.append('file', inputFile);
      const res = await fetch('http://localhost:8000/upload', { method: 'POST', body: fd });
      const j = await res.json();

      if(j.job_id){
        setMessage('Processing started — generating report...');
        const url = `http://localhost:8000/processed/${j.job_id}/report.html`;
        setReportUrl(url);
        setMessage('Done — click Open Report when ready');
      } else {
        setMessage('Upload finished — check backend logs');
      }
    }catch(err){
      console.error(err);
      setMessage('Upload failed — see console');
    }
    setLoading(false);
  }

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div>
          <div className="logo">One Click Analysis</div>
          <nav style={{marginTop:20}}>
            <a href="#">Dashboard</a>
            <a href="#">Reports</a>
            <a href="#">Models</a>
            <a href="#">Settings</a>
          </nav>
        </div>
        <div className="footer">v1.0 • Local mode</div>
      </aside>

      <main className="main-content">
        <header className="header">AI Data Analysis • Upload & Report</header>

        <section className="upload-card">
          <label className="file-label">Upload dataset (CSV / XLSX / JSON)</label>
          <input type="file" onChange={(e)=>setFile(e.target.files[0])} />
          <div style={{marginTop:16}}>
            <button className="btn-primary" onClick={()=>file && uploadFile(file)} disabled={!file || loading}>
              {loading ? 'Working...' : 'Generate Report'}
            </button>
          </div>

          {message && <div style={{marginTop:12}} className="success-box"><p>{message}</p></div>}

          {reportUrl && (
            <div style={{marginTop:16}}>
              <a href={reportUrl} target="_blank" rel="noreferrer"><button className="btn-secondary">Open Report</button></a>
            </div>
          )}
        </section>

        <section style={{marginTop:30}}>
          <div style={{display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:16}}>
            <div className="card">
              <h4>Quick Tips</h4>
              <ul>
                <li>Preferred formats: CSV / XLSX</li>
                <li>Large files: increase backend upload limits</li>
                <li>Data stays local — nothing uploaded to cloud</li>
              </ul>
            </div>
            <div className="card">
              <h4>Pipeline</h4>
              <ol>
                <li>ETL & Clean</li>
                <li>EDA & Visuals</li>
                <li>AutoML training</li>
                <li>Report generation</li>
              </ol>
            </div>
            <div className="card">
              <h4>Status</h4>
              <p>{loading ? 'Processing...' : 'Idle'}</p>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}

/* styles.css (imported) - paste your completed CSS into frontend/src/styles.css */
