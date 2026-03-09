import React, { useState } from 'react';
import { X, Type, Palette, Square } from 'lucide-react';

const FormattingPanel = ({ chart, onUpdate, onClose }) => {
    const [activeTab, setActiveTab] = useState('title');

    if (!chart) return null;

    const tabs = [
        { id: 'title', label: 'Title', icon: Type },
        { id: 'background', label: 'Background', icon: Square },
        // Chart and Analytics tabs removed - not applicable for static chart images
    ];

    const updateFormatting = (section, key, value) => {
        const newFormatting = {
            ...chart.formatting,
            [section]: {
                ...(chart.formatting?.[section] || {}),
                [key]: value
            }
        };
        onUpdate({ ...chart, formatting: newFormatting });
    };

    const updateChartFormatting = (key, value) => {
        const newChartFormatting = {
            ...(chart.chartFormatting || {}),
            [key]: value
        };
        onUpdate({ ...chart, chartFormatting: newChartFormatting });
    };

    return (
        <div style={{
            width: '320px',
            background: 'var(--bg-card)',
            borderLeft: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            height: '100%'
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
                    <Palette size={18} />
                    <span style={{ fontWeight: 'bold' }}>Format Visual</span>
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
                borderBottom: '1px solid var(--border)',
                padding: '0 0.5rem'
            }}>
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        style={{
                            flex: 1,
                            padding: '0.75rem 0.5rem',
                            background: 'transparent',
                            border: 'none',
                            borderBottom: activeTab === tab.id ? '2px solid var(--primary)' : '2px solid transparent',
                            color: activeTab === tab.id ? 'var(--primary)' : 'var(--text-secondary)',
                            cursor: 'pointer',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            gap: '0.25rem',
                            fontSize: '0.7rem'
                        }}
                    >
                        <tab.icon size={16} />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'auto', padding: '1rem' }}>
                {activeTab === 'title' && (
                    <TitleTab chart={chart} updateFormatting={updateFormatting} onUpdate={onUpdate} />
                )}
                {activeTab === 'background' && (
                    <BackgroundTab chart={chart} updateFormatting={updateFormatting} />
                )}
                {/* Chart and Analytics tabs removed - not applicable for static chart images */}
            </div>
        </div>
    );
};

// Title Tab Component
const TitleTab = ({ chart, updateFormatting, onUpdate }) => {
    const titleFormatting = chart.formatting?.title || {};

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <FormGroup label="Title Text">
                <input
                    type="text"
                    value={chart.customTitle || chart.title}
                    onChange={(e) => onUpdate({ ...chart, customTitle: e.target.value })}
                    style={inputStyle}
                />
            </FormGroup>

            <FormGroup label="Font Size">
                <input
                    type="range"
                    min="10"
                    max="32"
                    value={titleFormatting.size || 14}
                    onChange={(e) => updateFormatting('title', 'size', parseInt(e.target.value))}
                    style={{ width: '100%' }}
                />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {titleFormatting.size || 14}px
                </span>
            </FormGroup>

            <FormGroup label="Text Color">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                        type="color"
                        value={chart.titleColor || '#1e293b'}
                        onChange={(e) => onUpdate({ ...chart, titleColor: e.target.value })}
                        style={colorInputStyle}
                    />
                    <span style={{ fontSize: '0.8rem' }}>{chart.titleColor || '#1e293b'}</span>
                </div>
            </FormGroup>

            <FormGroup label="Alignment">
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {['left', 'center', 'right'].map(align => (
                        <button
                            key={align}
                            onClick={() => updateFormatting('title', 'alignment', align)}
                            style={{
                                ...buttonStyle,
                                flex: 1,
                                background: titleFormatting.alignment === align ? 'var(--primary)' : 'white',
                                color: titleFormatting.alignment === align ? 'white' : 'var(--text-primary)',
                            }}
                        >
                            {align.charAt(0).toUpperCase() + align.slice(1)}
                        </button>
                    ))}
                </div>
            </FormGroup>

            <FormGroup label="Font Weight">
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {['normal', 'bold'].map(weight => (
                        <button
                            key={weight}
                            onClick={() => updateFormatting('title', 'fontWeight', weight)}
                            style={{
                                ...buttonStyle,
                                flex: 1,
                                background: titleFormatting.fontWeight === weight ? 'var(--primary)' : 'white',
                                color: titleFormatting.fontWeight === weight ? 'white' : 'var(--text-primary)',
                                fontWeight: weight
                            }}
                        >
                            {weight.charAt(0).toUpperCase() + weight.slice(1)}
                        </button>
                    ))}
                </div>
            </FormGroup>

            <FormGroup label="Show Title">
                <ToggleSwitch
                    checked={titleFormatting.visible !== false}
                    onChange={(val) => updateFormatting('title', 'visible', val)}
                />
            </FormGroup>
        </div>
    );
};

// Background Tab Component
const BackgroundTab = ({ chart, updateFormatting }) => {
    const bgFormatting = chart.formatting?.background || {};
    const borderFormatting = chart.formatting?.border || {};
    const shadowFormatting = chart.formatting?.shadow || {};

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <SectionHeader>Background</SectionHeader>

            <FormGroup label="Background Color">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                        type="color"
                        value={chart.bgColor || '#ffffff'}
                        onChange={(e) => updateFormatting('background', 'color', e.target.value)}
                        style={colorInputStyle}
                    />
                    <span style={{ fontSize: '0.8rem' }}>{chart.bgColor || '#ffffff'}</span>
                </div>
            </FormGroup>

            <FormGroup label="Transparency">
                <input
                    type="range"
                    min="0"
                    max="100"
                    value={bgFormatting.transparency || 0}
                    onChange={(e) => updateFormatting('background', 'transparency', parseInt(e.target.value))}
                    style={{ width: '100%' }}
                />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {bgFormatting.transparency || 0}%
                </span>
            </FormGroup>

            <SectionHeader>Border</SectionHeader>

            <FormGroup label="Border Width">
                <input
                    type="range"
                    min="0"
                    max="10"
                    value={borderFormatting.width || 1}
                    onChange={(e) => updateFormatting('border', 'width', parseInt(e.target.value))}
                    style={{ width: '100%' }}
                />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {borderFormatting.width || 1}px
                </span>
            </FormGroup>

            <FormGroup label="Border Color">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                        type="color"
                        value={borderFormatting.color || '#e2e8f0'}
                        onChange={(e) => updateFormatting('border', 'color', e.target.value)}
                        style={colorInputStyle}
                    />
                    <span style={{ fontSize: '0.8rem' }}>{borderFormatting.color || '#e2e8f0'}</span>
                </div>
            </FormGroup>

            <FormGroup label="Border Radius">
                <input
                    type="range"
                    min="0"
                    max="24"
                    value={borderFormatting.radius || 12}
                    onChange={(e) => updateFormatting('border', 'radius', parseInt(e.target.value))}
                    style={{ width: '100%' }}
                />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {borderFormatting.radius || 12}px
                </span>
            </FormGroup>

            <SectionHeader>Shadow</SectionHeader>

            <FormGroup label="Enable Shadow">
                <ToggleSwitch
                    checked={shadowFormatting.enabled !== false}
                    onChange={(val) => updateFormatting('shadow', 'enabled', val)}
                />
            </FormGroup>

            {shadowFormatting.enabled !== false && (
                <>
                    <FormGroup label="Shadow Blur">
                        <input
                            type="range"
                            min="0"
                            max="30"
                            value={shadowFormatting.blur || 4}
                            onChange={(e) => updateFormatting('shadow', 'blur', parseInt(e.target.value))}
                            style={{ width: '100%' }}
                        />
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            {shadowFormatting.blur || 4}px
                        </span>
                    </FormGroup>

                    <FormGroup label="Shadow Color">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <input
                                type="color"
                                value={shadowFormatting.color || '#00000020'}
                                onChange={(e) => updateFormatting('shadow', 'color', e.target.value)}
                                style={colorInputStyle}
                            />
                        </div>
                    </FormGroup>
                </>
            )}
        </div>
    );
};

// Chart Tab Component
const ChartTab = ({ chart, updateChartFormatting }) => {
    const chartFormatting = chart.chartFormatting || {};

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <SectionHeader>Data Colors</SectionHeader>

            <FormGroup label="Color Mode">
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {['single', 'gradient', 'category'].map(mode => (
                        <button
                            key={mode}
                            onClick={() => updateChartFormatting('colorMode', mode)}
                            style={{
                                ...buttonStyle,
                                flex: 1,
                                background: chartFormatting.colorMode === mode ? 'var(--primary)' : 'white',
                                color: chartFormatting.colorMode === mode ? 'white' : 'var(--text-primary)',
                                fontSize: '0.7rem'
                            }}
                        >
                            {mode.charAt(0).toUpperCase() + mode.slice(1)}
                        </button>
                    ))}
                </div>
            </FormGroup>

            <FormGroup label="Primary Color">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                        type="color"
                        value={chartFormatting.primaryColor || '#3b82f6'}
                        onChange={(e) => updateChartFormatting('primaryColor', e.target.value)}
                        style={colorInputStyle}
                    />
                    <span style={{ fontSize: '0.8rem' }}>{chartFormatting.primaryColor || '#3b82f6'}</span>
                </div>
            </FormGroup>

            <SectionHeader>Legend</SectionHeader>

            <FormGroup label="Show Legend">
                <ToggleSwitch
                    checked={chartFormatting.legendVisible !== false}
                    onChange={(val) => updateChartFormatting('legendVisible', val)}
                />
            </FormGroup>

            <FormGroup label="Legend Position">
                <select
                    value={chartFormatting.legendPosition || 'bottom'}
                    onChange={(e) => updateChartFormatting('legendPosition', e.target.value)}
                    style={selectStyle}
                >
                    <option value="top">Top</option>
                    <option value="bottom">Bottom</option>
                    <option value="left">Left</option>
                    <option value="right">Right</option>
                </select>
            </FormGroup>

            <SectionHeader>Data Labels</SectionHeader>

            <FormGroup label="Show Data Labels">
                <ToggleSwitch
                    checked={chartFormatting.dataLabelsVisible === true}
                    onChange={(val) => updateChartFormatting('dataLabelsVisible', val)}
                />
            </FormGroup>

            <FormGroup label="Label Precision">
                <select
                    value={chartFormatting.labelPrecision || 0}
                    onChange={(e) => updateChartFormatting('labelPrecision', parseInt(e.target.value))}
                    style={selectStyle}
                >
                    <option value="0">No decimals</option>
                    <option value="1">1 decimal</option>
                    <option value="2">2 decimals</option>
                </select>
            </FormGroup>

            <SectionHeader>Axis</SectionHeader>

            <FormGroup label="Show X Axis">
                <ToggleSwitch
                    checked={chartFormatting.xAxisVisible !== false}
                    onChange={(val) => updateChartFormatting('xAxisVisible', val)}
                />
            </FormGroup>

            <FormGroup label="Show Y Axis">
                <ToggleSwitch
                    checked={chartFormatting.yAxisVisible !== false}
                    onChange={(val) => updateChartFormatting('yAxisVisible', val)}
                />
            </FormGroup>

            <FormGroup label="Show Grid Lines">
                <ToggleSwitch
                    checked={chartFormatting.gridLinesVisible !== false}
                    onChange={(val) => updateChartFormatting('gridLinesVisible', val)}
                />
            </FormGroup>
        </div>
    );
};

// Analytics Tab Component
const AnalyticsTab = ({ chart, onUpdate }) => {
    const analytics = chart.analytics || {};

    const updateAnalytics = (key, value) => {
        onUpdate({
            ...chart,
            analytics: { ...analytics, [key]: value }
        });
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <SectionHeader>Reference Lines</SectionHeader>

            <FormGroup label="Average Line">
                <ToggleSwitch
                    checked={analytics.averageLine?.enabled === true}
                    onChange={(val) => updateAnalytics('averageLine', { enabled: val, color: '#ef4444' })}
                />
            </FormGroup>

            <FormGroup label="Min/Max Lines">
                <ToggleSwitch
                    checked={analytics.minMaxLines?.enabled === true}
                    onChange={(val) => updateAnalytics('minMaxLines', { enabled: val })}
                />
            </FormGroup>

            <SectionHeader>Trend Analysis</SectionHeader>

            <FormGroup label="Trend Line">
                <ToggleSwitch
                    checked={analytics.trendLine?.enabled === true}
                    onChange={(val) => updateAnalytics('trendLine', { enabled: val, type: 'linear' })}
                />
            </FormGroup>

            {analytics.trendLine?.enabled && (
                <FormGroup label="Trend Type">
                    <select
                        value={analytics.trendLine?.type || 'linear'}
                        onChange={(e) => updateAnalytics('trendLine', { ...analytics.trendLine, type: e.target.value })}
                        style={selectStyle}
                    >
                        <option value="linear">Linear</option>
                        <option value="exponential">Exponential</option>
                        <option value="polynomial">Polynomial</option>
                    </select>
                </FormGroup>
            )}

            <SectionHeader>Constant Lines</SectionHeader>

            <FormGroup label="Add Constant Line">
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                        type="number"
                        placeholder="Value"
                        style={{ ...inputStyle, flex: 2 }}
                        id="constantLineValue"
                    />
                    <input
                        type="color"
                        defaultValue="#22c55e"
                        style={{ ...colorInputStyle, flex: 1 }}
                        id="constantLineColor"
                    />
                    <button
                        onClick={() => {
                            const value = document.getElementById('constantLineValue').value;
                            const color = document.getElementById('constantLineColor').value;
                            if (value) {
                                const lines = [...(analytics.constantLines || []), { value: parseFloat(value), color }];
                                updateAnalytics('constantLines', lines);
                                document.getElementById('constantLineValue').value = '';
                            }
                        }}
                        style={{ ...buttonStyle, background: 'var(--primary)', color: 'white' }}
                    >
                        +
                    </button>
                </div>
            </FormGroup>

            {analytics.constantLines?.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {analytics.constantLines.map((line, idx) => (
                        <span
                            key={idx}
                            style={{
                                padding: '0.25rem 0.5rem',
                                background: line.color + '20',
                                border: `1px solid ${line.color}`,
                                borderRadius: '4px',
                                fontSize: '0.75rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.25rem'
                            }}
                        >
                            {line.value}
                            <button
                                onClick={() => {
                                    const lines = analytics.constantLines.filter((_, i) => i !== idx);
                                    updateAnalytics('constantLines', lines);
                                }}
                                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: line.color }}
                            >
                                ×
                            </button>
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

// Reusable Components
const FormGroup = ({ label, children }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <label style={{ fontSize: '0.8rem', fontWeight: '500', color: 'var(--text-secondary)' }}>
            {label}
        </label>
        {children}
    </div>
);

const SectionHeader = ({ children }) => (
    <div style={{
        fontSize: '0.75rem',
        fontWeight: 'bold',
        textTransform: 'uppercase',
        color: 'var(--text-secondary)',
        paddingBottom: '0.5rem',
        borderBottom: '1px solid var(--border)',
        marginTop: '0.5rem'
    }}>
        {children}
    </div>
);

const ToggleSwitch = ({ checked, onChange }) => (
    <div
        onClick={() => onChange(!checked)}
        style={{
            width: '48px',
            height: '24px',
            background: checked ? 'var(--primary)' : '#e2e8f0',
            borderRadius: '12px',
            cursor: 'pointer',
            position: 'relative',
            transition: 'background 0.2s'
        }}
    >
        <div style={{
            width: '20px',
            height: '20px',
            background: 'white',
            borderRadius: '50%',
            position: 'absolute',
            top: '2px',
            left: checked ? '26px' : '2px',
            transition: 'left 0.2s',
            boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
        }} />
    </div>
);

// Styles
const inputStyle = {
    padding: '0.5rem',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    fontSize: '0.85rem',
    width: '100%',
    boxSizing: 'border-box'
};

const colorInputStyle = {
    width: '40px',
    height: '32px',
    padding: 0,
    border: '1px solid var(--border)',
    borderRadius: '6px',
    cursor: 'pointer'
};

const buttonStyle = {
    padding: '0.5rem',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.8rem',
    background: 'white'
};

const selectStyle = {
    padding: '0.5rem',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    fontSize: '0.85rem',
    width: '100%',
    background: 'white'
};

export default FormattingPanel;
