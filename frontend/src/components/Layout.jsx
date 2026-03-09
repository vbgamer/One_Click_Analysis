import React, { useState } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, Settings, LogOut, Menu, User } from 'lucide-react';
import '../styles/variables.css';

const Layout = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [isSidebarOpen, setSidebarOpen] = useState(true);

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    const navItems = [
        { label: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard size={20} /> },
        { label: 'My Reports', path: '/history', icon: <FileText size={20} /> },
        { label: 'Settings', path: '/settings', icon: <Settings size={20} /> },
    ];

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
                    <div style={{ width: '32px', height: '32px', background: 'var(--primary)', borderRadius: '8px' }}></div>
                    {isSidebarOpen && <h2 style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>OneClick</h2>}
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

                <button
                    onClick={handleLogout}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '1rem',
                        padding: '0.8rem',
                        color: 'var(--danger)',
                        cursor: 'pointer',
                        background: 'transparent',
                        border: 'none',
                        marginTop: 'auto'
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
                <header style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '2rem'
                }}>
                    <button onClick={() => setSidebarOpen(!isSidebarOpen)} style={{ color: 'var(--text-primary)' }}>
                        <Menu size={24} />
                    </button>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            background: 'var(--primary-soft)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'var(--primary-dark)'
                        }}>
                            <User size={20} />
                        </div>
                    </div>
                </header>

                <Outlet />
            </main>
        </div>
    );
};

export default Layout;
