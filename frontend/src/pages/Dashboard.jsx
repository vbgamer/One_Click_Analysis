import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, AlertCircle } from 'lucide-react';
import api from '../api';
import OnboardingTour from '../components/OnboardingTour';
import safeStorage from '../utils/storage';

const Dashboard = () => {
    const [isDragging, setIsDragging] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [showTour, setShowTour] = useState(false);
    const fileInputRef = useRef(null);
    const navigate = useNavigate();

    const [user, setUser] = useState(null);

    useEffect(() => {
        const checkUserAndTour = async () => {
            try {
                const response = await api.get('/users/me');
                const userData = response.data;
                setUser(userData);

                const hasSeenTour = safeStorage.getItem(`hasSeenDashboardTour_${userData.id}`);
                if (!hasSeenTour) {
                    setShowTour(true);
                }
            } catch (err) {
                console.error("Failed to fetch user for tour check", err);
            }
        };
        checkUserAndTour();
    }, []);

    const handleTourComplete = () => {
        setShowTour(false);
        if (user) {
            safeStorage.setItem(`hasSeenDashboardTour_${user.id}`, 'true');
        }
    };


    const tourSteps = [
        {
            targetId: 'dashboard-title',
            title: 'Welcome to One Click Analysis! 👋',
            description: 'This is your command center. From here, you can start new AI analyses.'
        },
        {
            targetId: 'upload-dropzone',
            title: 'Upload Your Data',
            description: 'Simply drag & drop your CSV or Excel file here. Our AI will automatically clean it, visualize it, and train models for you.'
        },
        {
            targetId: 'sidebar-nav', // Assuming Sidebar has this ID (we need to check Layout)
            title: 'Analyze & Review',
            description: 'Use the sidebar to view your past Reports, check System Status, or manage Settings.'
        }
    ];

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = async (e) => {
        e.preventDefault();
        setIsDragging(false);
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            await uploadFile(files[0]);
        }
    };

    const handleChange = async (e) => {
        const files = e.target.files;
        if (files.length > 0) {
            await uploadFile(files[0]);
        }
    };

    const uploadFile = async (file) => {
        setError('');
        setLoading(true);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await api.post('/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            // Redirect to status page
            navigate(`/status/${response.data.id}`);
        } catch (err) {
            console.error(err);
            setError('Upload failed. Please try again.');
            setLoading(false);
        }
    };

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <h1 id="dashboard-title" style={{ marginBottom: '1rem', color: 'var(--primary-dark)' }}>Create New Analysis</h1>
            <p style={{ marginBottom: '2rem', color: 'var(--text-secondary)' }}>
                Upload your dataset to generate a comprehensive AI-powered report.
                Supported formats: CSV, Excel, JSON.
            </p>

            <div
                id="upload-dropzone"
                className="card"
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                style={{
                    border: `2px dashed ${isDragging ? 'var(--primary)' : 'var(--border)'}`,
                    backgroundColor: isDragging ? 'var(--primary-soft)' : 'var(--bg-card)',
                    textAlign: 'center',
                    padding: '4rem 2rem',
                    cursor: 'pointer',
                    transition: 'var(--transition)'
                }}
                onClick={() => fileInputRef.current?.click()}
            >
                <input
                    type="file"
                    ref={fileInputRef}
                    style={{ display: 'none' }}
                    onChange={handleChange}
                    accept=".csv,.xlsx,.xls,.json"
                />

                <div style={{
                    width: '80px',
                    height: '80px',
                    background: 'var(--bg-input)',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 1.5rem',
                    color: 'var(--primary)'
                }}>
                    <UploadCloud size={40} />
                </div>

                <h3 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>
                    {loading ? 'Uploading...' : 'Click or Drag file to upload'}
                </h3>
                <p style={{ color: 'var(--text-secondary)' }}>
                    Up to 50MB. We handle the cleaning and processing.
                </p>
            </div>

            {error && (
                <div style={{
                    marginTop: '1.5rem',
                    padding: '1rem',
                    background: '#fee2e2',
                    color: '#ef4444',
                    borderRadius: 'var(--radius)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                }}>
                    <AlertCircle size={20} />
                    {error}
                </div>
            )}

            {showTour && <OnboardingTour steps={tourSteps} onComplete={handleTourComplete} />}
        </div>
    );
};

export default Dashboard;
