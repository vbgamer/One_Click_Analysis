import React, { useState, useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';

const Settings = () => {
    const [isDark, setIsDark] = useState(false);

    useEffect(() => {
        // Check initial usage
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            setIsDark(true);
            document.documentElement.setAttribute('data-theme', 'dark');
        }
    }, []);

    const toggleTheme = () => {
        const newTheme = !isDark;
        setIsDark(newTheme);
        if (newTheme) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    };

    return (
        <div style={{ maxWidth: '600px', margin: '0 auto' }}>
            <h1 style={{ marginBottom: '2rem' }}>Settings</h1>

            <div className="card">
                <h3 style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>Preferences</h3>

                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.5rem 0'
                }}>
                    <div>
                        <h4 style={{ marginBottom: '0.3rem' }}>Appearance</h4>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                            Switch between light and dark mode.
                        </p>
                    </div>

                    <button
                        onClick={toggleTheme}
                        className="btn btn-outline"
                        style={{ minWidth: '100px' }}
                    >
                        {isDark ? (
                            <>
                                <Sun size={18} /> Light
                            </>
                        ) : (
                            <>
                                <Moon size={18} /> Dark
                            </>
                        )}
                    </button>
                </div>
            </div>

            <div className="card" style={{ marginTop: '2rem' }}>
                <h3 style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>Account</h3>
                {/* Account details could go here, currently just static for demo */}
                <div style={{ color: 'var(--text-secondary)' }}>
                    Logged in via generic email auth.
                </div>
            </div>
        </div>
    );
};

export default Settings;
