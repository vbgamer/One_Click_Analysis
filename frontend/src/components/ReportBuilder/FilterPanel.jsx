import React, { useState } from 'react';
import { Filter, X, Plus, Trash2 } from 'lucide-react';

const FilterPanel = ({ chart, onUpdate, onClose }) => {
    const [activeTab, setActiveTab] = useState('basic');
    const [newFilterValue, setNewFilterValue] = useState('');

    if (!chart) return null;

    const filters = chart.filters || { basic: [], advanced: [], topN: { enabled: false, count: 10, by: 'value' } };

    const updateFilters = (newFilters) => {
        onUpdate({ ...chart, filters: newFilters });
    };

    const addBasicFilter = () => {
        if (!newFilterValue.trim()) return;
        const newBasic = [...(filters.basic || []), { value: newFilterValue, included: true }];
        updateFilters({ ...filters, basic: newBasic });
        setNewFilterValue('');
    };

    const removeBasicFilter = (index) => {
        const newBasic = filters.basic.filter((_, i) => i !== index);
        updateFilters({ ...filters, basic: newBasic });
    };

    const toggleBasicFilter = (index) => {
        const newBasic = filters.basic.map((f, i) =>
            i === index ? { ...f, included: !f.included } : f
        );
        updateFilters({ ...filters, basic: newBasic });
    };

    const updateAdvancedFilter = (key, value) => {
        updateFilters({
            ...filters,
            advanced: [{ ...filters.advanced?.[0], [key]: value }]
        });
    };

    const updateTopN = (key, value) => {
        updateFilters({
            ...filters,
            topN: { ...filters.topN, [key]: value }
        });
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
                width: '400px',
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
                        <Filter size={18} />
                        <span style={{ fontWeight: 'bold' }}>Visual Filters</span>
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

                {/* Tabs */}
                <div style={{
                    display: 'flex',
                    borderBottom: '1px solid var(--border)'
                }}>
                    {['basic', 'advanced', 'topN'].map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            style={{
                                flex: 1,
                                padding: '0.75rem',
                                background: 'transparent',
                                border: 'none',
                                borderBottom: activeTab === tab ? '2px solid var(--primary)' : '2px solid transparent',
                                color: activeTab === tab ? 'var(--primary)' : 'var(--text-secondary)',
                                cursor: 'pointer',
                                fontSize: '0.85rem'
                            }}
                        >
                            {tab === 'topN' ? 'Top N' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div style={{ flex: 1, overflow: 'auto', padding: '1rem' }}>
                    {activeTab === 'basic' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                Include or exclude specific values
                            </p>

                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <input
                                    type="text"
                                    value={newFilterValue}
                                    onChange={(e) => setNewFilterValue(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && addBasicFilter()}
                                    placeholder="Add filter value..."
                                    style={{
                                        flex: 1,
                                        padding: '0.5rem',
                                        border: '1px solid var(--border)',
                                        borderRadius: '6px',
                                        fontSize: '0.85rem'
                                    }}
                                />
                                <button
                                    onClick={addBasicFilter}
                                    style={{
                                        padding: '0.5rem 1rem',
                                        background: 'var(--primary)',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.25rem'
                                    }}
                                >
                                    <Plus size={16} />
                                </button>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                {filters.basic?.map((filter, idx) => (
                                    <div
                                        key={idx}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            padding: '0.5rem',
                                            background: filter.included ? '#dcfce7' : '#fee2e2',
                                            border: `1px solid ${filter.included ? '#22c55e' : '#ef4444'}`,
                                            borderRadius: '6px'
                                        }}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={filter.included}
                                            onChange={() => toggleBasicFilter(idx)}
                                        />
                                        <span style={{ flex: 1, fontSize: '0.85rem' }}>{filter.value}</span>
                                        <button
                                            onClick={() => removeBasicFilter(idx)}
                                            style={{
                                                background: 'transparent',
                                                border: 'none',
                                                cursor: 'pointer',
                                                color: 'var(--danger)'
                                            }}
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {activeTab === 'advanced' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                Create advanced filter conditions
                            </p>

                            <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
                                    Condition
                                </label>
                                <select
                                    value={filters.advanced?.[0]?.operator || 'contains'}
                                    onChange={(e) => updateAdvancedFilter('operator', e.target.value)}
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        border: '1px solid var(--border)',
                                        borderRadius: '6px',
                                        fontSize: '0.85rem'
                                    }}
                                >
                                    <option value="contains">Contains</option>
                                    <option value="not_contains">Does not contain</option>
                                    <option value="starts_with">Starts with</option>
                                    <option value="ends_with">Ends with</option>
                                    <option value="equals">Equals</option>
                                    <option value="not_equals">Not equals</option>
                                    <option value="greater_than">Greater than</option>
                                    <option value="less_than">Less than</option>
                                    <option value="between">Between</option>
                                </select>
                            </div>

                            <div>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
                                    Value
                                </label>
                                <input
                                    type="text"
                                    value={filters.advanced?.[0]?.value || ''}
                                    onChange={(e) => updateAdvancedFilter('value', e.target.value)}
                                    placeholder="Filter value..."
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

                            {filters.advanced?.[0]?.operator === 'between' && (
                                <div>
                                    <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
                                        End Value
                                    </label>
                                    <input
                                        type="text"
                                        value={filters.advanced?.[0]?.endValue || ''}
                                        onChange={(e) => updateAdvancedFilter('endValue', e.target.value)}
                                        placeholder="End value..."
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
                        </div>
                    )}

                    {activeTab === 'topN' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                Show only top or bottom N items
                            </p>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input
                                    type="checkbox"
                                    checked={filters.topN?.enabled || false}
                                    onChange={(e) => updateTopN('enabled', e.target.checked)}
                                />
                                <span style={{ fontSize: '0.85rem' }}>Enable Top N filtering</span>
                            </div>

                            {filters.topN?.enabled && (
                                <>
                                    <div>
                                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
                                            Show
                                        </label>
                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                            <select
                                                value={filters.topN?.mode || 'top'}
                                                onChange={(e) => updateTopN('mode', e.target.value)}
                                                style={{
                                                    padding: '0.5rem',
                                                    border: '1px solid var(--border)',
                                                    borderRadius: '6px',
                                                    fontSize: '0.85rem'
                                                }}
                                            >
                                                <option value="top">Top</option>
                                                <option value="bottom">Bottom</option>
                                            </select>
                                            <input
                                                type="number"
                                                min="1"
                                                max="100"
                                                value={filters.topN?.count || 10}
                                                onChange={(e) => updateTopN('count', parseInt(e.target.value))}
                                                style={{
                                                    width: '80px',
                                                    padding: '0.5rem',
                                                    border: '1px solid var(--border)',
                                                    borderRadius: '6px',
                                                    fontSize: '0.85rem'
                                                }}
                                            />
                                            <span style={{ alignSelf: 'center', fontSize: '0.85rem' }}>items</span>
                                        </div>
                                    </div>

                                    <div>
                                        <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem' }}>
                                            By
                                        </label>
                                        <select
                                            value={filters.topN?.by || 'value'}
                                            onChange={(e) => updateTopN('by', e.target.value)}
                                            style={{
                                                width: '100%',
                                                padding: '0.5rem',
                                                border: '1px solid var(--border)',
                                                borderRadius: '6px',
                                                fontSize: '0.85rem'
                                            }}
                                        >
                                            <option value="value">Value</option>
                                            <option value="count">Count</option>
                                            <option value="sum">Sum</option>
                                            <option value="average">Average</option>
                                        </select>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div style={{
                    padding: '1rem',
                    borderTop: '1px solid var(--border)',
                    display: 'flex',
                    gap: '0.5rem'
                }}>
                    <button
                        onClick={() => {
                            updateFilters({ basic: [], advanced: [], topN: { enabled: false } });
                        }}
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
                        Clear All
                    </button>
                    <button
                        onClick={onClose}
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
                        Apply Filters
                    </button>
                </div>
            </div>
        </>
    );
};

export default FilterPanel;
