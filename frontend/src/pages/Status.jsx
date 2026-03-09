import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import api from '../api';

const Status = () => {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const [job, setJob] = useState(null);
    const [error, setError] = useState(false);

    useEffect(() => {
        let interval;

        const checkStatus = async () => {
            try {
                const response = await api.get(`/status/${jobId}`);
                setJob(response.data);

                if (response.data.status === 'done') {
                    clearInterval(interval);
                    // Wait a moment to show completion state
                    setTimeout(() => {
                        navigate(`/report/${jobId}`);
                    }, 1000);
                } else if (response.data.status === 'failed') {
                    clearInterval(interval);
                    setError(true);
                }
            } catch (err) {
                console.error(err);
                clearInterval(interval);
                setError(true);
            }
        };

        // Initial check
        checkStatus();
        // Poll every 2 seconds
        interval = setInterval(checkStatus, 2000);

        return () => clearInterval(interval);
    }, [jobId, navigate]);

    if (error) {
        return (
            <div style={{ textAlign: 'center', marginTop: '4rem' }}>
                <div style={{ color: 'var(--danger)', marginBottom: '1rem' }}><AlertCircle size={64} /></div>
                <h2>Analysis Failed</h2>
                <p>Something went wrong while processing your file.</p>
                <button className="btn btn-outline" style={{ marginTop: '1rem' }} onClick={() => navigate('/dashboard')}>
                    Back to Dashboard
                </button>
            </div>
        );
    }

    return (
        <div style={{
            maxWidth: '600px',
            margin: '4rem auto',
            textAlign: 'center'
        }}>
            <div className="card">
                {job?.status === 'done' ? (
                    <div style={{ color: 'var(--success)' }}>
                        <CheckCircle size={64} style={{ margin: '0 auto 1rem' }} />
                        <h2>Analysis Complete!</h2>
                        <p>Redirecting to report...</p>
                    </div>
                ) : (
                    <div>
                        <div style={{
                            display: 'flex',
                            justifyContent: 'center',
                            marginBottom: '1.5rem',
                            animation: 'spin 2s linear infinite'
                        }}>
                            <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
                            <Loader2 size={64} color="var(--primary)" />
                        </div>
                        <h2>Processing Your Data...</h2>
                        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                            We are cleaning data, training models, and generating insights.
                        </p>
                        <div style={{ marginTop: '2rem', background: 'var(--bg-input)', padding: '1rem', borderRadius: 'var(--radius)' }}>
                            <strong>Status:</strong> {job ? job.status.toUpperCase() : 'LOADING...'}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Status;
