import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowRight, Check } from 'lucide-react';

const OnboardingTour = ({ steps, onComplete }) => {
    const [currentStep, setCurrentStep] = useState(0);
    const [position, setPosition] = useState({ top: 0, left: 0, width: 0, height: 0 });

    useEffect(() => {
        const updatePosition = () => {
            const step = steps[currentStep];
            if (!step || !step.targetId) return;

            const element = document.getElementById(step.targetId);
            if (element) {
                const rect = element.getBoundingClientRect();
                setPosition({
                    top: rect.top,
                    left: rect.left,
                    width: rect.width,
                    height: rect.height,
                });
            }
        };

        updatePosition();
        window.addEventListener('resize', updatePosition);
        return () => window.removeEventListener('resize', updatePosition);
    }, [currentStep, steps]);

    const handleNext = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(currentStep + 1);
        } else {
            onComplete();
        }
    };

    const step = steps[currentStep];

    // Calculate Tooltip Position
    let tooltipStyle = {
        position: 'absolute',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        padding: '20px',
        borderRadius: '12px',
        width: '300px',
        pointerEvents: 'auto',
        boxShadow: 'var(--shadow-lg)'
    };

    // If target is very tall (like sidebar), place to the right
    if (position.height > 300) {
        tooltipStyle.top = position.top + 50;
        tooltipStyle.left = position.left + position.width + 20;
    } else {
        // Default: Below the user element
        tooltipStyle.top = position.top + position.height + 20;
        tooltipStyle.left = position.left;

        // Check for right overflow
        if (tooltipStyle.left + 300 > window.innerWidth) {
            tooltipStyle.left = window.innerWidth - 320; // Anchor to right
        }
    }

    return (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 9999, pointerEvents: 'none' }}>
            {/* Dark Overlay with cutout */}
            <div style={{
                position: 'absolute',
                top: 0, left: 0, width: '100%', height: '100%',
                background: 'rgba(0,0,0,0.7)',
                clipPath: `polygon(
            0% 0%, 
            0% 100%, 
            100% 100%, 
            100% 0%, 
            0% 0%, 
            ${position.left}px ${position.top}px, 
            ${position.left + position.width}px ${position.top}px, 
            ${position.left + position.width}px ${position.top + position.height}px, 
            ${position.left}px ${position.top + position.height}px, 
            ${position.left}px ${position.top}px
          )`
            }} />

            {/* Spotlight Border */}
            <motion.div
                layout
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                style={{
                    position: 'absolute',
                    top: position.top - 4,
                    left: position.left - 4,
                    width: position.width + 8,
                    height: position.height + 8,
                    border: '2px solid var(--primary)',
                    borderRadius: '8px',
                    boxShadow: '0 0 20px var(--primary-glow)',
                    pointerEvents: 'none'
                }}
            />

            {/* Tooltip */}
            <motion.div
                key={currentStep}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                style={tooltipStyle}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <h4 style={{ margin: 0, color: 'var(--primary)', fontWeight: 'bold' }}>{step.title}</h4>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{currentStep + 1} / {steps.length}</span>
                </div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '20px' }}>
                    {step.description}
                </p>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                    {currentStep > 0 && (
                        <button
                            onClick={() => setCurrentStep(currentStep - 1)}
                            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                        >Back</button>
                    )}
                    <button
                        onClick={handleNext}
                        className="btn btn-primary"
                        style={{ fontSize: '0.9rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '5px' }}
                    >
                        {currentStep === steps.length - 1 ? 'Finish' : 'Next'} <ArrowRight size={14} />
                    </button>
                </div>
            </motion.div>
        </div>
    );
};

export default OnboardingTour;
