import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Download, ExternalLink, Send, Sparkles, MessageSquare, X, Settings } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../api';

const ReportView = () => {
    const { jobId } = useParams();
    const [reportUrl, setReportUrl] = useState('');
    const [loading, setLoading] = useState(true);

    const [chatOpen, setChatOpen] = useState(true);
    const [messages, setMessages] = useState([
        { role: 'assistant', text: "Hello! I'm your AI Data Analyst. Ask me anything about this report or dataset." }
    ]);
    const [input, setInput] = useState('');
    const [chatLoading, setChatLoading] = useState(false);
    const iframeRef = useRef(null);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        const fetchReport = async () => {
            try {
                const response = await api.get(`/status/${jobId}`);
                if (response.data.report_url) {
                    // Use relative URL to allow iframe manipulation (Same-Origin)
                    // Vite proxy will handle the request to backend
                    setReportUrl(response.data.report_url);
                }
            } catch (err) {
                console.error("Failed to load report", err);
            } finally {
                setLoading(false);
            }
        };
        fetchReport();
    }, [jobId]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleDownloadPDF = () => {
        if (iframeRef.current && iframeRef.current.contentWindow) {
            iframeRef.current.contentWindow.focus();
            iframeRef.current.contentWindow.print();
        }
    };

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg = input;
        setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
        setInput('');
        setChatLoading(true);

        try {
            const response = await api.post('/chat', {
                job_id: jobId,
                message: userMsg
            });
            setMessages(prev => [...prev, { role: 'assistant', text: response.data.reply }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', text: "Sorry, I encountered an error answering that." }]);
        } finally {
            setChatLoading(false);
        }
    };

    if (loading) return <div className="card">Loading Report...</div>;
    if (!reportUrl) return <div className="card">Report not found.</div>;

    return (
        <div style={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column' }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1rem',
                padding: '0 1rem'
            }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>Analysis Report</h2>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setChatOpen(!chatOpen)}
                        className="btn btn-primary"
                        style={{ display: 'flex', alignItems: 'center', gap: '8px', background: chatOpen ? 'var(--primary-dark)' : 'var(--primary)' }}
                    >
                        {chatOpen ? <X size={18} /> : <Sparkles size={18} />}
                        {chatOpen ? 'Hide Assistant' : 'Chat with Data'}
                    </motion.button>

                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => window.location.href = `/builder/${jobId}`}
                        className="btn btn-primary"
                        style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--primary)' }}
                    >
                        <Settings size={18} /> Customize Report
                    </motion.button>


                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                        <button onClick={handleDownloadPDF} className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#dc2626' }}>
                            <Download size={18} /> Download PDF
                        </button>
                        <a href={reportUrl} download style={{ fontSize: '0.8rem', color: '#64748b', textDecoration: 'underline' }}>
                            Download raw HTML
                        </a>
                    </div>

                    <a href={reportUrl} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
                        <ExternalLink size={18} /> Open in New Tab
                    </a>
                </div>
            </div>

            <div style={{ display: 'flex', flex: 1, gap: '20px', overflow: 'hidden', padding: '0 1rem 1rem 1rem' }}>
                {/* Report Iframe */}
                <motion.div
                    initial={{ flex: 1 }}
                    animate={{ flex: 1 }}
                    style={{
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius)',
                        overflow: 'hidden',
                        background: 'white',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    }}>
                    <iframe
                        ref={iframeRef}
                        src={reportUrl}
                        title="Analysis Report"
                        style={{ width: '100%', height: '100%', border: 'none' }}
                    />
                </motion.div>

                {/* Chat Details Sidebar */}
                <AnimatePresence>
                    {chatOpen && (
                        <motion.div
                            initial={{ width: 0, opacity: 0, x: 20 }}
                            animate={{ width: 380, opacity: 1, x: 0 }}
                            exit={{ width: 0, opacity: 0, x: 20 }}
                            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                            style={{
                                display: 'flex',
                                flexDirection: 'column',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--radius)',
                                background: 'white',
                                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                                overflow: 'hidden'
                            }}
                        >
                            <div style={{
                                padding: '15px 20px',
                                borderBottom: '1px solid var(--border)',
                                background: 'linear-gradient(to right, #f8fafc, #fff)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px'
                            }}>
                                <div style={{
                                    background: 'var(--primary-light)',
                                    padding: '8px',
                                    borderRadius: '8px',
                                    color: 'var(--primary)'
                                }}>
                                    <Sparkles size={20} />
                                </div>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 'bold', color: '#1e293b' }}>AI Data Analyst</h3>
                                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Online & Ready to help</span>
                                </div>
                            </div>

                            <div style={{
                                flex: 1,
                                overflowY: 'auto',
                                padding: '20px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '16px',
                                background: '#f8fafc'
                            }}>
                                {messages.map((msg, idx) => (
                                    <motion.div
                                        key={idx}
                                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                        animate={{ opacity: 1, y: 0, scale: 1 }}
                                        style={{
                                            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                            maxWidth: '85%',
                                        }}
                                    >
                                        <div style={{
                                            background: msg.role === 'user' ? 'var(--primary)' : 'white',
                                            color: msg.role === 'user' ? 'white' : 'black', /* Requested: Black text for assistant */
                                            padding: '12px 16px',
                                            borderRadius: msg.role === 'user' ? '16px 16px 0 16px' : '16px 16px 16px 0',
                                            fontSize: '0.9rem',
                                            lineHeight: '1.5',
                                            boxShadow: msg.role !== 'user' ? '0 2px 4px rgba(0,0,0,0.05)' : 'none',
                                            border: msg.role !== 'user' ? '1px solid #e2e8f0' : 'none'
                                        }}>
                                            {msg.text}
                                        </div>
                                        <div style={{
                                            fontSize: '0.7rem',
                                            color: '#94a3b8',
                                            marginTop: '4px',
                                            textAlign: msg.role === 'user' ? 'right' : 'left',
                                            padding: '0 4px'
                                        }}>
                                            {msg.role === 'user' ? 'You' : 'AI Analyst'}
                                        </div>
                                    </motion.div>
                                ))}
                                {chatLoading && (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        style={{ alignSelf: 'flex-start', background: 'white', padding: '10px 16px', borderRadius: '16px', border: '1px solid #e2e8f0' }}
                                    >
                                        <div style={{ display: 'flex', gap: '4px' }}>
                                            <motion.div
                                                animate={{ y: [0, -5, 0] }}
                                                transition={{ repeat: Infinity, duration: 0.6 }}
                                                style={{ width: '6px', height: '6px', background: '#94a3b8', borderRadius: '50%' }}
                                            />
                                            <motion.div
                                                animate={{ y: [0, -5, 0] }}
                                                transition={{ repeat: Infinity, duration: 0.6, delay: 0.2 }}
                                                style={{ width: '6px', height: '6px', background: '#94a3b8', borderRadius: '50%' }}
                                            />
                                            <motion.div
                                                animate={{ y: [0, -5, 0] }}
                                                transition={{ repeat: Infinity, duration: 0.6, delay: 0.4 }}
                                                style={{ width: '6px', height: '6px', background: '#94a3b8', borderRadius: '50%' }}
                                            />
                                        </div>
                                    </motion.div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            <div style={{ padding: '15px 20px', borderTop: '1px solid var(--border)', background: 'white' }}>
                                <div style={{
                                    display: 'flex',
                                    gap: '8px',
                                    background: '#f1f5f9',
                                    padding: '8px',
                                    borderRadius: '12px',
                                    border: '1px solid #e2e8f0'
                                }}>
                                    <input
                                        type="text"
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                                        placeholder="Ask a question about your data..."
                                        style={{
                                            flex: 1,
                                            background: 'transparent',
                                            border: 'none',
                                            outline: 'none',
                                            padding: '4px 8px',
                                            fontSize: '0.9rem',
                                            color: '#334155'
                                        }}
                                    />
                                    <motion.button
                                        whileHover={{ scale: 1.1 }}
                                        whileTap={{ scale: 0.9 }}
                                        onClick={handleSend}
                                        className="btn btn-primary"
                                        style={{
                                            padding: '8px',
                                            borderRadius: '8px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center'
                                        }}
                                        disabled={chatLoading}
                                    >
                                        <Send size={16} />
                                    </motion.button>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default ReportView;
