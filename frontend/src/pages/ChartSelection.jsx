import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Check, ArrowRight, BarChart2 } from 'lucide-react';
import api from '../api';

const ChartSelection = () => {
    const { jobId } = useParams();
    const navigate = useNavigate();

    const [charts, setCharts] = useState([]);
    const [selectedCharts, setSelectedCharts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const loadCharts = async () => {
            try {
                setLoading(true);
                const res = await api.get(`/reports/${jobId}/charts`);
                // Flatten all chart categories into a single array
                const allCharts = [];
                for (const [category, items] of Object.entries(res.data)) {
                    if (Array.isArray(items)) {
                        items.forEach(item => {
                            allCharts.push({ ...item, category });
                        });
                    }
                }
                setCharts(allCharts);
            } catch (err) {
                console.error("Error loading charts:", err);
                setError("Failed to load charts. Please try again.");
            } finally {
                setLoading(false);
            }
        };
        loadCharts();
    }, [jobId]);

    const toggleChart = (chartPath) => {
        setSelectedCharts(prev => {
            if (prev.includes(chartPath)) {
                return prev.filter(p => p !== chartPath);
            } else {
                return [...prev, chartPath];
            }
        });
    };

    const handleNext = () => {
        if (selectedCharts.length < 3) {
            alert("Please select at least 3 charts to continue.");
            return;
        }
        // Navigate to layout builder with selected charts
        navigate(`/builder/${jobId}/layout`, {
            state: {
                selectedCharts: charts.filter(c => selectedCharts.includes(c.path))
            }
        });
    };

    if (loading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                background: 'var(--background)',
                color: 'var(--text-primary)'
            }}>
                <div style={{ textAlign: 'center' }}>
                    <BarChart2 size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                    <p>Loading charts...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                background: 'var(--background)',
                color: 'var(--text-primary)'
            }}>
                <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                    <p style={{ color: 'var(--danger)' }}>{error}</p>
                    <button onClick={() => navigate(-1)} className="btn btn-primary" style={{ marginTop: '1rem' }}>
                        Go Back
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{
            minHeight: '100vh',
            background: 'var(--background)',
            color: 'var(--text-primary)',
            padding: '2rem'
        }}>
            {/* Header */}
            <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
                <div style={{ marginBottom: '2rem' }}>
                    <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                        Customize Your Report
                    </h1>
                    <p style={{ color: 'var(--text-secondary)' }}>
                        Select the charts you want to include in your custom dashboard.
                        <span style={{
                            color: selectedCharts.length >= 3 ? 'var(--success)' : 'var(--warning)',
                            fontWeight: 'bold',
                            marginLeft: '0.5rem'
                        }}>
                            ({selectedCharts.length} selected, minimum 3 required)
                        </span>
                    </p>
                </div>

                {/* Charts Grid */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                    gap: '1.5rem',
                    marginBottom: '6rem' // Space for fixed footer
                }}>
                    {charts.map((chart) => {
                        const isSelected = selectedCharts.includes(chart.path);
                        return (
                            <motion.div
                                key={chart.path}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => toggleChart(chart.path)}
                                style={{
                                    background: 'var(--bg-card)',
                                    border: isSelected ? '2px solid var(--primary)' : '1px solid var(--border)',
                                    borderRadius: '12px',
                                    overflow: 'hidden',
                                    cursor: 'pointer',
                                    position: 'relative',
                                    transition: 'all 0.2s ease'
                                }}
                            >
                                {/* Selection indicator */}
                                <div style={{
                                    position: 'absolute',
                                    top: '10px',
                                    right: '10px',
                                    width: '28px',
                                    height: '28px',
                                    borderRadius: '50%',
                                    background: isSelected ? 'var(--primary)' : 'rgba(255,255,255,0.9)',
                                    border: isSelected ? 'none' : '2px solid var(--border)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    zIndex: 10
                                }}>
                                    {isSelected && <Check size={16} color="white" />}
                                </div>

                                {/* Chart preview */}
                                <div style={{
                                    height: '180px',
                                    background: '#f8fafc',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    overflow: 'hidden'
                                }}>
                                    <img
                                        src={`/static/charts/${jobId}/${chart.path}`}
                                        alt={chart.title}
                                        style={{
                                            maxWidth: '100%',
                                            maxHeight: '100%',
                                            objectFit: 'contain'
                                        }}
                                        onError={(e) => {
                                            e.target.style.display = 'none';
                                            e.target.parentElement.innerHTML = '<div style="color:#9ca3af">Preview unavailable</div>';
                                        }}
                                    />
                                </div>

                                {/* Chart info */}
                                <div style={{ padding: '1rem' }}>
                                    <h3 style={{
                                        fontSize: '0.95rem',
                                        fontWeight: '600',
                                        marginBottom: '0.25rem',
                                        color: 'var(--text-primary)'
                                    }}>
                                        {chart.title}
                                    </h3>
                                    <span style={{
                                        fontSize: '0.75rem',
                                        color: 'var(--text-secondary)',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.05em'
                                    }}>
                                        {chart.category}
                                    </span>
                                </div>
                            </motion.div>
                        );
                    })}
                </div>

                {/* Fixed Footer with Next Button */}
                <div style={{
                    position: 'fixed',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    padding: '1.5rem 2rem',
                    background: 'var(--bg-card)',
                    borderTop: '1px solid var(--border)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    zIndex: 100
                }}>
                    <button
                        onClick={() => navigate(-1)}
                        className="btn btn-outline"
                        style={{ padding: '0.75rem 1.5rem' }}
                    >
                        Cancel
                    </button>

                    <motion.button
                        whileHover={{ scale: selectedCharts.length >= 3 ? 1.02 : 1 }}
                        whileTap={{ scale: selectedCharts.length >= 3 ? 0.98 : 1 }}
                        onClick={handleNext}
                        className="btn btn-primary"
                        style={{
                            padding: '0.75rem 2rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            opacity: selectedCharts.length >= 3 ? 1 : 0.5,
                            cursor: selectedCharts.length >= 3 ? 'pointer' : 'not-allowed'
                        }}
                    >
                        Next
                        <ArrowRight size={18} />
                    </motion.button>
                </div>
            </div>
        </div>
    );
};

export default ChartSelection;
