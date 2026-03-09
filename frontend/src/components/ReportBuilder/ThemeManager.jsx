import React, { useState } from 'react';
import { Paintbrush, X, Check } from 'lucide-react';

// Preset themes
const presetThemes = [
    {
        id: 'default',
        name: 'Default',
        colors: {
            primary: '#3b82f6',
            secondary: '#64748b',
            accent: '#8b5cf6',
            background: '#f1f5f9',
            cardBg: '#ffffff',
            text: '#1e293b',
            border: '#e2e8f0'
        }
    },
    {
        id: 'dark',
        name: 'Dark Mode',
        colors: {
            primary: '#60a5fa',
            secondary: '#94a3b8',
            accent: '#a78bfa',
            background: '#0f172a',
            cardBg: '#1e293b',
            text: '#f1f5f9',
            border: '#334155'
        }
    },
    {
        id: 'ocean',
        name: 'Ocean Blue',
        colors: {
            primary: '#0ea5e9',
            secondary: '#06b6d4',
            accent: '#14b8a6',
            background: '#ecfeff',
            cardBg: '#ffffff',
            text: '#0c4a6e',
            border: '#bae6fd'
        }
    },
    {
        id: 'forest',
        name: 'Forest Green',
        colors: {
            primary: '#22c55e',
            secondary: '#16a34a',
            accent: '#84cc16',
            background: '#f0fdf4',
            cardBg: '#ffffff',
            text: '#14532d',
            border: '#bbf7d0'
        }
    },
    {
        id: 'sunset',
        name: 'Sunset Orange',
        colors: {
            primary: '#f97316',
            secondary: '#ea580c',
            accent: '#eab308',
            background: '#fff7ed',
            cardBg: '#ffffff',
            text: '#7c2d12',
            border: '#fed7aa'
        }
    },
    {
        id: 'royal',
        name: 'Royal Purple',
        colors: {
            primary: '#8b5cf6',
            secondary: '#7c3aed',
            accent: '#ec4899',
            background: '#faf5ff',
            cardBg: '#ffffff',
            text: '#581c87',
            border: '#e9d5ff'
        }
    },
    {
        id: 'corporate',
        name: 'Corporate',
        colors: {
            primary: '#0f172a',
            secondary: '#475569',
            accent: '#2563eb',
            background: '#f8fafc',
            cardBg: '#ffffff',
            text: '#1e293b',
            border: '#cbd5e1'
        }
    },
    {
        id: 'warm',
        name: 'Warm Earth',
        colors: {
            primary: '#b45309',
            secondary: '#a16207',
            accent: '#dc2626',
            background: '#fffbeb',
            cardBg: '#ffffff',
            text: '#713f12',
            border: '#fde68a'
        }
    }
];

const ThemeManager = ({ currentTheme, onApplyTheme, onClose }) => {
    const [selectedTheme, setSelectedTheme] = useState(currentTheme?.id || 'default');
    const [customColors, setCustomColors] = useState(currentTheme?.colors || presetThemes[0].colors);
    const [isCustom, setIsCustom] = useState(false);

    const handleApply = () => {
        if (isCustom) {
            onApplyTheme({ id: 'custom', name: 'Custom', colors: customColors });
        } else {
            const theme = presetThemes.find(t => t.id === selectedTheme);
            onApplyTheme(theme);
        }
        onClose();
    };

    return (
        <>
            <div
                onClick={onClose}
                style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0,0,0,0.5)',
                    zIndex: 999
                }}
            />
            <div style={{
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
                width: '500px',
                maxHeight: '80vh',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                zIndex: 1000
            }}>
                {/* Header */}
                <div style={{
                    padding: '1rem',
                    borderBottom: '1px solid var(--border)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Paintbrush size={18} />
                        <span style={{ fontWeight: 'bold' }}>Report Theme</span>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--text-secondary)'
                        }}
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Theme Grid */}
                <div style={{ flex: 1, overflow: 'auto', padding: '1rem' }}>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                        Select a theme to apply consistent styling across all visuals
                    </p>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(2, 1fr)',
                        gap: '1rem',
                        marginBottom: '1.5rem'
                    }}>
                        {presetThemes.map(theme => (
                            <div
                                key={theme.id}
                                onClick={() => { setSelectedTheme(theme.id); setIsCustom(false); }}
                                style={{
                                    border: selectedTheme === theme.id && !isCustom
                                        ? '2px solid var(--primary)'
                                        : '1px solid var(--border)',
                                    borderRadius: '8px',
                                    padding: '0.75rem',
                                    cursor: 'pointer',
                                    background: theme.colors.cardBg,
                                    position: 'relative'
                                }}
                            >
                                {selectedTheme === theme.id && !isCustom && (
                                    <div style={{
                                        position: 'absolute',
                                        top: '0.5rem',
                                        right: '0.5rem',
                                        background: 'var(--primary)',
                                        borderRadius: '50%',
                                        width: '20px',
                                        height: '20px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }}>
                                        <Check size={12} color="white" />
                                    </div>
                                )}

                                <div style={{
                                    fontSize: '0.85rem',
                                    fontWeight: '500',
                                    marginBottom: '0.5rem',
                                    color: theme.colors.text
                                }}>
                                    {theme.name}
                                </div>

                                {/* Color preview */}
                                <div style={{ display: 'flex', gap: '4px' }}>
                                    {Object.entries(theme.colors).slice(0, 5).map(([key, color]) => (
                                        <div
                                            key={key}
                                            style={{
                                                width: '24px',
                                                height: '24px',
                                                borderRadius: '4px',
                                                background: color,
                                                border: '1px solid rgba(0,0,0,0.1)'
                                            }}
                                            title={key}
                                        />
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Custom Theme */}
                    <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                            <input
                                type="checkbox"
                                checked={isCustom}
                                onChange={(e) => setIsCustom(e.target.checked)}
                            />
                            <span style={{ fontSize: '0.85rem', fontWeight: '500' }}>Use Custom Colors</span>
                        </div>

                        {isCustom && (
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
                                {Object.entries(customColors).map(([key, color]) => (
                                    <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <input
                                            type="color"
                                            value={color}
                                            onChange={(e) => setCustomColors(prev => ({ ...prev, [key]: e.target.value }))}
                                            style={{
                                                width: '32px',
                                                height: '32px',
                                                padding: 0,
                                                border: '1px solid var(--border)',
                                                borderRadius: '4px',
                                                cursor: 'pointer'
                                            }}
                                        />
                                        <span style={{ fontSize: '0.8rem', textTransform: 'capitalize' }}>
                                            {key.replace(/([A-Z])/g, ' $1').trim()}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div style={{
                    padding: '1rem',
                    borderTop: '1px solid var(--border)',
                    display: 'flex',
                    gap: '0.5rem'
                }}>
                    <button
                        onClick={onClose}
                        style={{
                            flex: 1,
                            padding: '0.75rem',
                            background: 'transparent',
                            color: 'var(--text-secondary)',
                            border: '1px solid var(--border)',
                            borderRadius: '6px',
                            cursor: 'pointer'
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleApply}
                        style={{
                            flex: 1,
                            padding: '0.75rem',
                            background: 'var(--primary)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontWeight: 'bold'
                        }}
                    >
                        Apply Theme
                    </button>
                </div>
            </div>
        </>
    );
};

export default ThemeManager;
