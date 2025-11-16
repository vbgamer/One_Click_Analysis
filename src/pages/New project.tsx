import React, { useState } from 'react';
import { Upload, File, AlertCircle } from 'lucide-react';
import '../styles/NewProject.css';

const NewProject: React.FC = () => {
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState('');
  const [projectName, setProjectName] = useState('');

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      setFileName(files[0].name);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      setFileName(files[0].name);
    }
  };

  return (
    <div className="new-project">
      <div className="project-header">
        <h2>Create New Project</h2>
        <p>Upload your CSV or Excel file to start analyzing</p>
      </div>

      <div className="project-form">
        <div className="form-group">
          <label htmlFor="projectName">Project Name</label>
          <input
            id="projectName"
            type="text"
            placeholder="Enter a descriptive project name"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="form-input"
          />
        </div>

        <div className="form-group">
          <label>Upload File</label>
          <div
            className={`upload-area ${dragActive ? 'active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <div className="upload-content">
              <Upload size={48} className="upload-icon" />
              <h3>Drag and drop your file here</h3>
              <p>or click to browse</p>
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleChange}
                className="file-input"
              />
              <div className="supported-formats">
                <File size={16} />
                <span>CSV, XLS, XLSX</span>
              </div>
            </div>
          </div>

          {fileName && (
            <div className="file-selected">
              <File size={20} />
              <span>{fileName}</span>
            </div>
          )}
        </div>

        <div className="info-box">
          <AlertCircle size={20} />
          <div>
            <h4>File Requirements</h4>
            <ul>
              <li>Maximum file size: 50MB</li>
              <li>Supported formats: CSV, XLS, XLSX</li>
              <li>First row should contain column headers</li>
            </ul>
          </div>
        </div>

        <div className="form-actions">
          <button className="btn-primary" disabled={!projectName || !fileName}>
            Create & Analyze
          </button>
          <button className="btn-secondary">Cancel</button>
        </div>
      </div>
    </div>
  );
};

export default NewProject;
