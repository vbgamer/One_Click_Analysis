import React, { useState } from 'react';
import api from '../api';

const CreditModal = ({ isOpen, onClose, onRequested }) => {
    const [amount, setAmount] = useState(500);
    const [note, setNote] = useState('');
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState('');

    if (!isOpen) return null;

    const handleRequest = async () => {
        setLoading(true);
        setError('');
        try {
            await api.post('/credits/request', { amount_requested: amount, note });
            setSent(true);
            if (onRequested) onRequested();
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to send request.');
        } finally {
            setLoading(false);
        }
    };

    const overlayStyle = {
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(4px)'
    };

    const cardStyle = {
        background: 'var(--bg-card, #1a1b2e)',
        border: '1px solid rgba(139,92,246,0.4)',
        borderRadius: '16px', padding: '36px', maxWidth: '440px', width: '90%',
        boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
        animation: 'slideUp 0.3s ease'
    };

    return (
        <div style={overlayStyle} onClick={onClose}>
            <div style={cardStyle} onClick={e => e.stopPropagation()}>
                {!sent ? (
                    <>
                        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                            <div style={{ fontSize: '3rem', marginBottom: '8px' }}>💳</div>
                            <h2 style={{ color: '#a78bfa', margin: 0, fontSize: '1.4rem' }}>Out of Credits</h2>
                            <p style={{ color: '#9ca3af', marginTop: '8px', fontSize: '0.9rem' }}>
                                You don't have enough credits to continue. Request additional credits from the admin — they'll be added to your account shortly.
                            </p>
                        </div>

                        <div style={{ marginBottom: '16px' }}>
                            <label style={{ color: '#d1d5db', fontSize: '0.85rem', display: 'block', marginBottom: '6px' }}>
                                Credits to Request
                            </label>
                            <input
                                type="number"
                                value={amount}
                                onChange={e => setAmount(parseInt(e.target.value) || 500)}
                                min="100"
                                step="100"
                                style={{
                                    width: '100%', padding: '10px', borderRadius: '8px',
                                    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(139,92,246,0.3)',
                                    color: 'white', fontSize: '1rem', boxSizing: 'border-box'
                                }}
                            />
                        </div>

                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ color: '#d1d5db', fontSize: '0.85rem', display: 'block', marginBottom: '6px' }}>
                                Note (optional)
                            </label>
                            <textarea
                                value={note}
                                onChange={e => setNote(e.target.value)}
                                placeholder="Why do you need more credits?"
                                rows={2}
                                style={{
                                    width: '100%', padding: '10px', borderRadius: '8px',
                                    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(139,92,246,0.3)',
                                    color: 'white', fontSize: '0.9rem', resize: 'none', boxSizing: 'border-box'
                                }}
                            />
                        </div>

                        {error && (
                            <p style={{ color: '#f87171', fontSize: '0.85rem', marginBottom: '12px' }}>{error}</p>
                        )}

                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button
                                onClick={onClose}
                                style={{
                                    flex: 1, padding: '10px', borderRadius: '8px', border: '1px solid #4b5563',
                                    background: 'transparent', color: '#9ca3af', cursor: 'pointer', fontSize: '0.9rem'
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleRequest}
                                disabled={loading}
                                style={{
                                    flex: 2, padding: '10px', borderRadius: '8px', border: 'none',
                                    background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                                    color: 'white', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem',
                                    opacity: loading ? 0.7 : 1
                                }}
                            >
                                {loading ? 'Sending...' : '📩 Request Credits from Admin'}
                            </button>
                        </div>
                    </>
                ) : (
                    <div style={{ textAlign: 'center', padding: '20px 0' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '12px' }}>✅</div>
                        <h2 style={{ color: '#34d399', margin: 0 }}>Request Sent!</h2>
                        <p style={{ color: '#9ca3af', marginTop: '12px' }}>
                            Your request for <strong style={{ color: 'white' }}>{amount} credits</strong> has been sent to the admin. You'll be notified once approved.
                        </p>
                        <button
                            onClick={onClose}
                            style={{
                                marginTop: '20px', padding: '10px 24px', borderRadius: '8px', border: 'none',
                                background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                                color: 'white', cursor: 'pointer', fontWeight: '600'
                            }}
                        >
                            Close
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CreditModal;
