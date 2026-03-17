import React, { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, Settings, LogOut, Menu, User, ShieldCheck } from 'lucide-react';
import '../styles/variables.css';
import api from '../api';
import CreditModal from './CreditModal';

const Layout = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [isSidebarOpen, setSidebarOpen] = useState(true);
    const [currentUser, setCurrentUser] = useState(null);
    const [showCreditModal, setShowCreditModal] = useState(false);

    // Fetch current user on mount
    useEffect(() => {
        api.get('/users/me')
            .then(res => setCurrentUser(res.data))
            .catch(() => { });
    }, []);

    // Listen for global 402 events fired by api.js interceptor
    useEffect(() => {
        const handler = () => setShowCreditModal(true);
        window.addEventListener('credits:insufficient', handler);
        return () => window.removeEventListener('credits:insufficient', handler);
    }, []);

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    const navItems = [
        { label: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard size={20} /> },
        { label: 'My Reports', path: '/history', icon: <FileText size={20} /> },
        { label: 'Settings', path: '/settings', icon: <Settings size={20} /> },
    ];

    if (currentUser?.role === 'admin') {
        navItems.push({ label: 'Admin Panel', path: '/admin', icon: <ShieldCheck size={20} /> });
    }

    const isInfinite = currentUser && currentUser.credits >= 99999999;
    const creditDisplay = isInfinite ? '∞' : (currentUser ? currentUser.credits.toLocaleString() : '...');
    const creditColor = isInfinite ? '#a78bfa' : (currentUser?.credits < 100 ? '#f87171' : '#34d399');

    return (
        <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
            {/* Sidebar */}
            <aside style={{
                width: isSidebarOpen ? '250px' : '70px',
                backgroundColor: 'var(--bg-sidebar)',
                color: 'white',
                padding: '1rem',
                transition: 'width 0.3s ease',
                display: 'flex',
                flexDirection: 'column',
                position: 'fixed',
                height: '100vh',
                zIndex: 10
            }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '3rem', gap: '1rem' }}>
                    <div style={{ width: '32px', height: '32px', background: 'var(--primary)', borderRadius: '8px', flexShrink: 0 }}></div>
                    {isSidebarOpen && <h2 style={{ fontSize: '1.2rem', fontWeight: 'bold', margin: 0 }}>OneClick</h2>}
                </div>

                <nav id="sidebar-nav" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {navItems.map((item) => (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={location.pathname === item.path ? 'active-nav' : ''}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '1rem',
                                padding: '0.8rem',
                                borderRadius: '8px',
                                color: location.pathname === item.path ? 'white' : 'var(--text-secondary)',
                                backgroundColor: location.pathname === item.path ? 'var(--primary)' : 'transparent',
                                textDecoration: 'none',
                                transition: '0.2s'
                            }}
                        >
                            {item.icon}
                            {isSidebarOpen && <span>{item.label}</span>}
                        </Link>
                    ))}
                </nav>

                {/* Credit Balance */}
                {isSidebarOpen && currentUser && (
                    <div
                        onClick={() => !isInfinite && currentUser.credits < 200 && setShowCreditModal(true)}
                        style={{
                            marginBottom: '12px',
                            padding: '12px',
                            background: 'rgba(255,255,255,0.05)',
                            borderRadius: '10px',
                            border: `1px solid ${creditColor}44`,
                            cursor: !isInfinite && currentUser.credits < 200 ? 'pointer' : 'default',
                        }}
                    >
                        <div style={{ fontSize: '0.7rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Credits</div>
                        <div style={{ fontSize: '1.4rem', fontWeight: '700', color: creditColor }}>{creditDisplay}</div>
                        {!isInfinite && currentUser.credits < 200 && (
                            <div style={{ fontSize: '0.7rem', color: '#f87171', marginTop: '4px' }}>Low — click to request more</div>
                        )}
                    </div>
                )}

                <button
                    onClick={handleLogout}
                    style={{
                        display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.8rem',
                        color: 'var(--danger)', cursor: 'pointer', background: 'transparent', border: 'none',
                    }}
                >
                    <LogOut size={20} />
                    {isSidebarOpen && <span>Logout</span>}
                </button>
            </aside>

            {/* Main Content */}
            <main style={{
                flex: 1,
                marginLeft: isSidebarOpen ? '250px' : '70px',
                transition: 'margin-left 0.3s ease',
                padding: '2rem'
            }}>
                <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                    <button onClick={() => setSidebarOpen(!isSidebarOpen)} style={{ color: 'var(--text-primary)', background: 'none', border: 'none', cursor: 'pointer' }}>
                        <Menu size={24} />
                    </button>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        {currentUser && (
                            <div
                                onClick={() => !isInfinite && currentUser.credits < 200 && setShowCreditModal(true)}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: '6px',
                                    padding: '6px 14px', borderRadius: '20px',
                                    background: `${creditColor}15`, border: `1px solid ${creditColor}44`,
                                    cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', color: creditColor
                                }}
                            >
                                💳 {creditDisplay} credits
                            </div>
                        )}
                        <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--primary-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary-dark)' }}>
                            <User size={20} />
                        </div>
                    </div>
                </header>

                <Outlet />
            </main>

            {/* Global Credit Modal */}
            <CreditModal
                isOpen={showCreditModal}
                onClose={() => setShowCreditModal(false)}
                onRequested={() => setShowCreditModal(false)}
            />
        </div>
    );
};

export default Layout;
