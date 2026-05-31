import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Loader2, CheckCircle, AlertCircle, Brain, FileText } from 'lucide-react';
import api from '../api';

const Status = () => {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const [job, setJob] = useState(null);
    const [error, setError] = useState(false);
    const [autoRedirect, setAutoRedirect] = useState(true);

    useEffect(() => {
        let interval;

        const checkStatus = async () => {
            try {
                const response = await api.get(`/status/${jobId}`);
                setJob(response.data);

                if (response.data.status === 'done') {
                    clearInterval(interval);
                    // Show completion UI with both options — don't auto-redirect
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

        checkStatus();
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
        <div style={{ maxWidth: '640px', margin: '4rem auto', textAlign: 'center' }}>
            <div className="card">
                {job?.status === 'done' ? (
                    <div>
                        <div style={{ color: 'var(--success)', marginBottom: '1rem' }}>
                            <CheckCircle size={64} style={{ margin: '0 auto' }} />
                        </div>
                        <h2 style={{ marginBottom: '0.5rem' }}>Analysis Complete! 🎉</h2>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
                            Your dataset has been processed. Choose how to explore it:
                        </p>

                        {/* Action buttons */}
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                            <Link
                                to={`/intelligence/${jobId}`}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '14px 24px',
                                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                    color: 'white',
                                    borderRadius: '10px',
                                    textDecoration: 'none',
                                    fontWeight: '600',
                                    fontSize: '15px',
                                    boxShadow: '0 0 20px rgba(99,102,241,0.4)',
                                    transition: 'transform 0.2s',
                                }}
                                onMouseOver={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                                onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}
                            >
                                <Brain size={20} />
                                🧠 AI Intelligence Dashboard
                            </Link>

                            <Link
                                to={`/report/${jobId}`}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '14px 24px',
                                    background: 'transparent',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border)',
                                    borderRadius: '10px',
                                    textDecoration: 'none',
                                    fontWeight: '500',
                                    fontSize: '15px',
                                }}
                            >
                                <FileText size={20} />
                                View Classic Report
                            </Link>
                        </div>

                        <p style={{ marginTop: '1.5rem', fontSize: '12px', color: 'var(--text-secondary)' }}>
                            💡 The AI Intelligence Dashboard gives you forecasting, anomaly detection, and conversational AI
                        </p>
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
                            Cleaning data, training models, and generating insights.
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
