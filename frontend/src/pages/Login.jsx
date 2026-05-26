import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import TermsModal from '../components/TermsModal';
import safeStorage from '../utils/storage';

const Login = () => {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [showTerms, setShowTerms] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        try {
            if (isLogin) {
                // Login: Expects x-www-form-urlencoded
                const params = new URLSearchParams();
                params.append('username', email);
                params.append('password', password);

                const response = await api.post('/auth/login', params, {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                });
                safeStorage.setItem('token', response.data.access_token);
                navigate('/dashboard');
            } else {
                // Signup
                await api.post('/auth/signup', { email, password, name });
                // Auto login after signup
                const params = new URLSearchParams();
                params.append('username', email);
                params.append('password', password);
                const loginResponse = await api.post('/auth/login', params, {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                });
                safeStorage.setItem('token', loginResponse.data.access_token);
                navigate('/dashboard');
            }
        } catch (err) {
            console.error("Auth Exception:", err);


            if (!err.response) {
                setError('Cannot connect to the backend server. Please make sure the app server is running, then refresh this page.');
            } else {
                setError(err.response?.data?.detail || 'Authentication failed. Please check your credentials.');
            }
        }
    };

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100vh',
            background: 'var(--bg-main)'
        }}>
            <div className="card" style={{ width: '400px' }}>
                <h1 style={{ marginBottom: '1.5rem', textAlign: 'center', color: 'var(--primary)' }}>
                    {isLogin ? 'Welcome Back' : 'Create Account'}
                </h1>

                {error && (
                    <div style={{
                        background: '#fee2e2',
                        color: '#ef4444',
                        padding: '0.8rem',
                        borderRadius: 'var(--radius)',
                        marginBottom: '1rem',
                        fontSize: '0.9rem'
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {!isLogin && (
                        <input
                            type="text"
                            placeholder="Full Name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                        />
                    )}
                    <input
                        type="email"
                        placeholder="Email Address"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoComplete="email"
                    />
                    <input
                        type="password"
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        autoComplete={isLogin ? "current-password" : "new-password"}
                    />

                    {!isLogin && (
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '0.85rem' }}>
                            <input
                                type="checkbox"
                                required
                                style={{ marginTop: '4px' }}
                                id="terms-check"
                            />
                            <label htmlFor="terms-check" style={{ color: 'var(--text-secondary)' }}>
                                I agree to the <span onClick={() => setShowTerms(true)} style={{ color: 'var(--primary)', cursor: 'pointer', textDecoration: 'underline' }}>Terms & Conditions</span> and confirm I am authorized to share company data.
                            </label>
                        </div>
                    )}

                    <button type="submit" className="btn btn-primary" style={{ marginTop: '0.5rem' }}>
                        {isLogin ? 'Sign In' : 'Sign Up'}
                    </button>
                </form>

                <p style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    {isLogin ? "Don't have an account? " : "Already have an account? "}
                    <span
                        onClick={() => setIsLogin(!isLogin)}
                        style={{ color: 'var(--primary)', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                        {isLogin ? 'Sign Up' : 'Login'}
                    </span>
                </p>
            </div>
            <TermsModal isOpen={showTerms} onClose={() => setShowTerms(false)} />
        </div>
    );
};

export default Login;
