import React, { useState } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, X } from 'lucide-react';

const SortingPanel = ({ chart, onUpdate, onClose }) => {
    if (!chart) return null;

    const sorting = chart.sorting || {};

    const updateSorting = (key, value) => {
        onUpdate({
            ...chart,
            sorting: { ...sorting, [key]: value }
        });
    };

    return (
        <div style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
            width: '320px',
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
                    <ArrowUpDown size={18} />
                    <span style={{ fontWeight: 'bold' }}>Sort Options</span>
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

            {/* Content */}
            <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                    <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
                        Sort By
                    </label>
                    <select
                        value={sorting.type || 'value'}
                        onChange={(e) => updateSorting('type', e.target.value)}
                        style={{
                            width: '100%',
                            padding: '0.5rem',
                            border: '1px solid var(--border)',
                            borderRadius: '6px',
                            fontSize: '0.85rem'
                        }}
                    >
                        <option value="value">Value (Measure)</option>
                        <option value="axis">Axis (Category)</option>
                        <option value="name">Name (Alphabetical)</option>
                        <option value="custom">Custom Order</option>
                    </select>
                </div>

                <div>
                    <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
                        Direction
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            onClick={() => updateSorting('direction', 'asc')}
                            style={{
                                flex: 1,
                                padding: '0.75rem',
                                border: '1px solid var(--border)',
                                borderRadius: '6px',
                                background: sorting.direction === 'asc' ? 'var(--primary)' : 'white',
                                color: sorting.direction === 'asc' ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.5rem'
                            }}
                        >
                            <ArrowUp size={16} />
                            Ascending
                        </button>
                        <button
                            onClick={() => updateSorting('direction', 'desc')}
                            style={{
                                flex: 1,
                                padding: '0.75rem',
                                border: '1px solid var(--border)',
                                borderRadius: '6px',
                                background: sorting.direction === 'desc' ? 'var(--primary)' : 'white',
                                color: sorting.direction === 'desc' ? 'white' : 'var(--text-primary)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.5rem'
                            }}
                        >
                            <ArrowDown size={16} />
                            Descending
                        </button>
                    </div>
                </div>

                {sorting.type === 'custom' && (
                    <div>
                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
                            Custom Order (comma-separated)
                        </label>
                        <input
                            type="text"
                            value={sorting.customOrder?.join(', ') || ''}
                            onChange={(e) => updateSorting('customOrder', e.target.value.split(',').map(s => s.trim()))}
                            placeholder="Item1, Item2, Item3..."
                            style={{
                                width: '100%',
                                padding: '0.5rem',
                                border: '1px solid var(--border)',
                                borderRadius: '6px',
                                fontSize: '0.85rem',
                                boxSizing: 'border-box'
                            }}
                        />
                    </div>
                )}

                <button
                    onClick={() => {
                        updateSorting('enabled', true);
                        onClose();
                    }}
                    style={{
                        width: '100%',
                        padding: '0.75rem',
                        background: 'var(--primary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontWeight: 'bold'
                    }}
                >
                    Apply Sort
                </button>

                {sorting.enabled && (
                    <button
                        onClick={() => {
                            onUpdate({ ...chart, sorting: null });
                            onClose();
                        }}
                        style={{
                            width: '100%',
                            padding: '0.5rem',
                            background: 'transparent',
                            color: 'var(--danger)',
                            border: '1px solid var(--danger)',
                            borderRadius: '6px',
                            cursor: 'pointer'
                        }}
                    >
                        Clear Sort
                    </button>
                )}
            </div>
        </div>
    );
};

// Overlay for modal
const SortingPanelWithOverlay = (props) => {
    if (!props.chart) return null;

    return (
        <>
            <div
                onClick={props.onClose}
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
            <SortingPanel {...props} />
        </>
    );
};

export default SortingPanelWithOverlay;
