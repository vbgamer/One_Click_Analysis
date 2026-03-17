import React, { useState, useEffect } from 'react';
import api from '../api';

const AdminDashboard = () => {
    const [tab, setTab] = useState('users');
    const [users, setUsers] = useState([]);
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(false);
    const [editCredits, setEditCredits] = useState({});
    const [msg, setMsg] = useState('');

    const fetchData = async () => {
        setLoading(true);
        try {
            const [u, r] = await Promise.all([
                api.get('/admin/users'),
                api.get('/admin/requests'),
            ]);
            setUsers(u.data);
            setRequests(r.data);
        } catch (err) {
            setMsg('Error fetching data: ' + (err.response?.data?.detail || err.message));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchData(); }, []);

    const handleCreditUpdate = async (userId) => {
        const newCredits = parseInt(editCredits[userId]);
        if (isNaN(newCredits)) return;
        try {
            await api.patch(`/admin/users/${userId}/credits`, { credits: newCredits });
            setMsg(`✅ Credits updated for user #${userId}`);
            fetchData();
        } catch (err) {
            setMsg('Error: ' + (err.response?.data?.detail || err.message));
        }
    };

    const handleRequest = async (reqId, action) => {
        try {
            await api.post(`/admin/requests/${reqId}/${action}`);
            setMsg(`✅ Request #${reqId} ${action}d`);
            fetchData();
        } catch (err) {
            setMsg('Error: ' + (err.response?.data?.detail || err.message));
        }
    };

    const pill = (text, color) => (
        <span style={{
            padding: '2px 10px', borderRadius: '99px', fontSize: '0.75rem', fontWeight: '600',
            background: color === 'green' ? 'rgba(52,211,153,0.15)' : color === 'red' ? 'rgba(248,113,113,0.15)' : 'rgba(251,191,36,0.15)',
            color: color === 'green' ? '#34d399' : color === 'red' ? '#f87171' : '#fbbf24',
        }}>{text}</span>
    );

    const btnStyle = (color) => ({
        padding: '6px 14px', borderRadius: '6px', border: 'none', cursor: 'pointer',
        fontWeight: '600', fontSize: '0.8rem',
        background: color === 'green' ? 'rgba(52,211,153,0.2)' : 'rgba(248,113,113,0.2)',
        color: color === 'green' ? '#34d399' : '#f87171',
    });

    return (
        <div style={{
            minHeight: '100vh', background: 'var(--bg-main, #0f0f1a)',
            padding: '30px', fontFamily: 'Inter, system-ui, sans-serif'
        }}>
            <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
                {/* Header */}
                <div style={{ marginBottom: '30px' }}>
                    <h1 style={{ color: '#a78bfa', margin: 0, fontSize: '1.8rem' }}>🛡️ Admin Control Panel</h1>
                    <p style={{ color: '#6b7280', marginTop: '6px' }}>Manage users, credits, and requests</p>
                </div>

                {msg && (
                    <div style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid #34d399', color: '#34d399', padding: '10px 16px', borderRadius: '8px', marginBottom: '20px', fontSize: '0.9rem' }}>
                        {msg}
                    </div>
                )}

                {/* Tabs */}
                <div style={{ display: 'flex', gap: '4px', marginBottom: '24px', background: 'rgba(255,255,255,0.05)', borderRadius: '10px', padding: '4px', width: 'max-content' }}>
                    {['users', 'requests'].map(t => (
                        <button
                            key={t}
                            onClick={() => setTab(t)}
                            style={{
                                padding: '8px 20px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                                fontWeight: '600', fontSize: '0.9rem', textTransform: 'capitalize',
                                background: tab === t ? 'linear-gradient(135deg,#7c3aed,#4f46e5)' : 'transparent',
                                color: tab === t ? 'white' : '#9ca3af',
                            }}
                        >
                            {t === 'users' ? '👥 Users' : '📩 Credit Requests'}
                        </button>
                    ))}
                </div>

                {/* Users Tab */}
                {tab === 'users' && (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr>
                                    {['ID', 'Name', 'Email', 'Role', 'Credits', 'Joined', 'Edit Credits'].map(h => (
                                        <th key={h} style={{ textAlign: 'left', padding: '10px 14px', color: '#6b7280', fontSize: '0.8rem', textTransform: 'uppercase', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {users.map(u => (
                                    <tr key={u.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                        <td style={{ padding: '12px 14px', color: '#4b5563', fontSize: '0.85rem' }}>#{u.id}</td>
                                        <td style={{ padding: '12px 14px', color: 'white', fontWeight: '500' }}>{u.name || '—'}</td>
                                        <td style={{ padding: '12px 14px', color: '#a78bfa' }}>{u.email}</td>
                                        <td style={{ padding: '12px 14px' }}>
                                            {u.role === 'admin' ? pill('Admin', 'green') : pill('User', 'yellow')}
                                        </td>
                                        <td style={{ padding: '12px 14px', color: u.credits > 100 ? '#34d399' : '#f87171', fontWeight: '700' }}>
                                            {u.credits >= 99999999 ? '∞' : u.credits.toLocaleString()}
                                        </td>
                                        <td style={{ padding: '12px 14px', color: '#6b7280', fontSize: '0.8rem' }}>
                                            {new Date(u.created_at).toLocaleDateString()}
                                        </td>
                                        <td style={{ padding: '12px 14px' }}>
                                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                                <input
                                                    type="number"
                                                    placeholder="Set credits"
                                                    value={editCredits[u.id] || ''}
                                                    onChange={e => setEditCredits(prev => ({ ...prev, [u.id]: e.target.value }))}
                                                    style={{
                                                        width: '100px', padding: '6px', borderRadius: '6px', fontSize: '0.85rem',
                                                        background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(139,92,246,0.3)', color: 'white'
                                                    }}
                                                />
                                                <button onClick={() => handleCreditUpdate(u.id)} style={btnStyle('green')}>Set</button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Requests Tab */}
                {tab === 'requests' && (
                    <div style={{ overflowX: 'auto' }}>
                        {requests.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '60px', color: '#4b5563' }}>
                                <div style={{ fontSize: '3rem' }}>📭</div>
                                <p>No credit requests yet</p>
                            </div>
                        ) : (
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr>
                                        {['ID', 'User ID', 'Amount', 'Note', 'Status', 'Date', 'Actions'].map(h => (
                                            <th key={h} style={{ textAlign: 'left', padding: '10px 14px', color: '#6b7280', fontSize: '0.8rem', textTransform: 'uppercase', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {requests.map(r => (
                                        <tr key={r.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                            <td style={{ padding: '12px 14px', color: '#4b5563' }}>#{r.id}</td>
                                            <td style={{ padding: '12px 14px', color: '#a78bfa' }}>User #{r.user_id}</td>
                                            <td style={{ padding: '12px 14px', color: '#34d399', fontWeight: '700' }}>{r.amount_requested.toLocaleString()}</td>
                                            <td style={{ padding: '12px 14px', color: '#9ca3af', fontSize: '0.85rem', maxWidth: '180px' }}>{r.note || '—'}</td>
                                            <td style={{ padding: '12px 14px' }}>
                                                {r.status === 'approved' ? pill('Approved', 'green')
                                                    : r.status === 'rejected' ? pill('Rejected', 'red')
                                                        : pill('Pending', 'yellow')}
                                            </td>
                                            <td style={{ padding: '12px 14px', color: '#6b7280', fontSize: '0.8rem' }}>{new Date(r.created_at).toLocaleDateString()}</td>
                                            <td style={{ padding: '12px 14px' }}>
                                                {r.status === 'pending' && (
                                                    <div style={{ display: 'flex', gap: '6px' }}>
                                                        <button onClick={() => handleRequest(r.id, 'approve')} style={btnStyle('green')}>✅ Approve</button>
                                                        <button onClick={() => handleRequest(r.id, 'reject')} style={btnStyle('red')}>❌ Reject</button>
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default AdminDashboard;
