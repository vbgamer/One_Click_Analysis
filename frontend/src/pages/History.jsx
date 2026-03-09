import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Calendar, ArrowRight, Trash2 } from 'lucide-react';
import api from '../api';

const History = () => {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const response = await api.get('/my-reports');
                setJobs(response.data);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, []);

    const handleDelete = async (jobId, e) => {
        // Prevent navigation if button is clicked inside a link (though it's outside here)
        e.preventDefault();

        if (!window.confirm("Are you sure you want to delete this analysis report and all associated data? This cannot be undone.")) {
            return;
        }

        try {
            await api.delete(`/reports/${jobId}`);
            // Optimistic update
            setJobs(jobs.filter(job => job.id !== jobId));
        } catch (err) {
            console.error(err);
            alert("Failed to delete report. Please try again.");
        }
    };

    if (loading) return <div>Loading history...</div>;

    return (
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
            <h1 style={{ marginBottom: '2rem' }}>My Reports</h1>

            {jobs.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                    <p style={{ color: 'var(--text-secondary)' }}>You haven't generated any reports yet.</p>
                    <Link to="/dashboard" className="btn btn-primary" style={{ marginTop: '1rem' }}>
                        Create New Analysis
                    </Link>
                </div>
            ) : (
                <div style={{ display: 'grid', gap: '1rem' }}>
                    {jobs.map((job) => (
                        <div key={job.id} className="card" style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div style={{
                                    background: 'var(--bg-input)',
                                    padding: '0.8rem',
                                    borderRadius: '8px',
                                    color: 'var(--primary)'
                                }}>
                                    <FileText size={24} />
                                </div>
                                <div>
                                    <h3 style={{ marginBottom: '0.2rem' }}>{job.filename}</h3>
                                    <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                            <Calendar size={14} />
                                            {new Date(job.created_at).toLocaleDateString()}
                                        </span>
                                        <span style={{
                                            color: job.status === 'done' ? 'var(--success)' : 'var(--warning)',
                                            fontWeight: 500
                                        }}>
                                            {job.status.toUpperCase()}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {job.status === 'done' && (
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button
                                        onClick={(e) => handleDelete(job.id, e)}
                                        className="btn btn-outline"
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            borderColor: '#ef4444',
                                            color: '#ef4444'
                                        }}
                                        title="Delete Report"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                    <Link to={`/report/${job.id}`} className="btn btn-outline" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        View Report <ArrowRight size={16} />
                                    </Link>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default History;
