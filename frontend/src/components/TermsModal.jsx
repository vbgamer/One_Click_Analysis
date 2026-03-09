import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ShieldAlert } from 'lucide-react';

const TermsModal = ({ isOpen, onClose }) => {
    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        background: 'rgba(0,0,0,0.6)',
                        backdropFilter: 'blur(5px)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 1000,
                        padding: '20px'
                    }}
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.9, opacity: 0 }}
                        style={{
                            background: 'var(--surface)',
                            width: '100%',
                            maxWidth: '600px',
                            borderRadius: 'var(--radius-lg)',
                            border: '1px solid var(--border)',
                            boxShadow: 'var(--shadow-lg)',
                            display: 'flex',
                            flexDirection: 'column',
                            maxHeight: '80vh'
                        }}
                    >
                        {/* Header */}
                        <div style={{
                            padding: '20px',
                            borderBottom: '1px solid var(--border)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                        }}>
                            <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Terms and Conditions</h2>
                            <button
                                onClick={onClose}
                                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
                            >
                                <X size={24} />
                            </button>
                        </div>

                        {/* Content */}
                        <div style={{ padding: '24px', overflowY: 'auto', lineHeight: '1.6', color: 'var(--text-secondary)' }}>

                            <div style={{
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid var(--danger)',
                                borderRadius: '8px',
                                padding: '16px',
                                marginBottom: '24px',
                                display: 'flex',
                                gap: '12px'
                            }}>
                                <ShieldAlert color="var(--danger)" size={24} style={{ minWidth: '24px' }} />
                                <div>
                                    <h3 style={{ color: 'var(--danger)', fontWeight: 'bold', marginBottom: '4px' }}>
                                        Data Privacy Warning
                                    </h3>
                                    <p style={{ fontSize: '0.9rem' }}>
                                        <strong>Are you ready to share your company data?</strong><br />
                                        By uploading files, you grant One Click Analysis permission to process your proprietary data using cloud-based AI models. Ensure you have authorization to share this data.
                                    </p>
                                </div>
                            </div>

                            <h3>1. Acceptance of Terms</h3>
                            <p>By creating an account, you agree to be bound by these Terms of Service.</p>

                            <h3>2. Data Processing</h3>
                            <p>We use automated algorithms to process your data. While we strive for accuracy, ML models may produce errors.</p>

                            <h3>3. User Responsibilities</h3>
                            <p>You are responsible for the confidentiality of your credentials and the data you upload.</p>

                        </div>

                        {/* Footer */}
                        <div style={{ padding: '20px', borderTop: '1px solid var(--border)', textAlign: 'right' }}>
                            <button onClick={onClose} className="btn btn-primary">I Understand</button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};

export default TermsModal;
