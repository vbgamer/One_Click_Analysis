import React, { useState } from "react";
import axios from "axios";
import "./styles.css";

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reportLink, setReportLink] = useState("");

  const handleUpload = async () => {
    if (!file) {
      alert("Please upload a file first.");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post("http://localhost:8000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const job_id = res.data.job_id;
      setReportLink(`http://localhost:8000/processed/${job_id}/report.html`);
    } catch (error) {
      console.error(error);
      alert("Upload failed. Check backend logs.");
    }

    setLoading(false);
  };

  return (
    <div className="app-container">
      <div className="main-content">
        <h1 style={{ margin: "20px" }}>📊 One Click Analysis</h1>

        <div style={{
          background: "white",
          padding: "30px",
          borderRadius: "10px",
          boxShadow: "var(--shadow)",
          maxWidth: "450px",
          margin: "auto",
          textAlign: "center"
        }}>
          
          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
            style={{ marginBottom: "20px" }}
          />

          {!loading ? (
            <button className="btn-primary" onClick={handleUpload}>
              🔍 Generate Report
            </button>
          ) : (
            <p>Processing... Please wait ⏳</p>
          )}

          {reportLink && (
            <div style={{ marginTop: "20px" }}>
              <a href={reportLink} target="_blank" rel="noopener noreferrer">
                <button className="btn-secondary">📄 Open Report</button>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
