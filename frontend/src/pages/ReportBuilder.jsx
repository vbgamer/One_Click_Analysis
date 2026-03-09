import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as RGL from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { Save, Layout, ArrowLeft, PaintBucket, Type, Sparkles, MonitorPlay } from 'lucide-react';
import api from '../api';
import _ from 'lodash';

console.log("RGL exports:", Object.keys(RGL));
const ResponsiveGridLayout = RGL.WidthProvider ? RGL.WidthProvider(RGL.Responsive || RGL.default) : RGL.default;

// Simple X icon for close button to avoid import conflict if not used elsewhere
const X = ({ size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
    </svg>
);

const ReportBuilder = () => {
    const { jobId } = useParams();
    const navigate = useNavigate();

    console.log("ReportBuilder mounting...", jobId);

    // State
    const [charts, setCharts] = useState({});
    const [layout, setLayout] = useState([]);
    const [draggingItem, setDraggingItem] = useState(null);
    const [reportTitle, setReportTitle] = useState('My Custom Dashboard');
    const [bgColor, setBgColor] = useState('#f3f4f6');
    const [customTitles, setCustomTitles] = useState({});
    const [dbNameInput, setDbNameInput] = useState('');
    const [sidebarOpen, setSidebarOpen] = useState(true);

    // Initial Load
    useEffect(() => {
        const loadData = async () => {
            try {
                const res = await api.get(`/reports/${jobId}/charts`);
                setCharts(res.data);
            } catch (err) {
                console.error("Error loading charts", err);
            }
        };
        loadData();
    }, [jobId]);

    // AI Agent Layout Generator
    const generateAiLayout = async () => {
        try {
            const res = await api.get(`/reports/${jobId}/ai-layout`);
            const aiLayout = res.data.layout;

            // Map the layout from backend to RGL format
            // Backend sends: { i, x, y, w, h }
            // We need to ensure 'i' matches our chart paths
            setLayout(aiLayout);
            alert("AI Agent has organized your dashboard!");
        } catch (err) {
            console.error("AI Layout failed", err);
            alert("AI Agent could not generate a layout. Please try manual drag-and-drop.");
        }
    };

    // Handling Drop from Sidebar
    const onDrop = (layout, layoutItem, _event) => {
        if (!draggingItem) return;

        // The item dropped has a generic 'i'. We need to replace it with the actual chart path info
        const newItem = {
            ...layoutItem,
            i: draggingItem.path, // Use actual chart path as ID
            w: 6, h: 4 // Default size
        };

        // Remove generic placeholder if RGL added one, add our real item
        const cleanLayout = layout.filter(l => l.i !== "__dropping-elem__");
        setLayout([...cleanLayout, newItem]);
    };

    const handlePublish = async () => {
        try {
            const payload = {
                title: reportTitle,
                selected_charts: layout.map(l => l.i),
                layout: layout,
                metadata: {
                    backgroundColor: bgColor,
                    itemTitles: customTitles
                }
            };

            const res = await api.post(`/reports/${jobId}/custom`, payload);
            if (res.data.report_url) {
                // Open in new tab (Full Screen)
                window.open(res.data.report_url, '_blank');
                // Or navigate to view
                // navigate(`/report/${jobId}`); 
            }
        } catch (err) {
            console.error("Publish failed", err);
            alert("Failed to publish report.");
        }
    };

    // Render Sidebar Item
    const renderSidebarItem = (item) => {
        return (
            <div
                key={item.path}
                className="draggable-chart"
                draggable={true}
                unselectable="on"
                onDragStart={(e) => {
                    setDraggingItem(item);
                    e.dataTransfer.setData("text/plain", "");
                }}
                style={{
                    padding: '10px',
                    border: '1px solid #e5e7eb',
                    marginBottom: '10px',
                    borderRadius: '8px',
                    cursor: 'grab',
                    background: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                }}
            >
                <div style={{ width: '40px', height: '40px', background: '#f9fafb', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem' }}>
                    📊
                </div>
                <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: '500', color: '#374151' }}>{item.title}</div>
                </div>
            </div>
        );
    };

    return (
        <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#f9fafb' }}>
            {/* Top Bar */}
            <div style={{
                height: '60px',
                background: 'white',
                borderBottom: '1px solid #e5e7eb',
                display: 'flex',
                alignItems: 'center',
                padding: '0 20px',
                justifyContent: 'space-between',
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                zIndex: 10
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <button onClick={() => navigate(-1)} className="btn btn-ghost" style={{ padding: '8px' }}>
                        <ArrowLeft size={20} color="#4b5563" />
                    </button>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <input
                            value={reportTitle}
                            onChange={(e) => setReportTitle(e.target.value)}
                            style={{
                                fontSize: '1.2rem',
                                fontWeight: '600',
                                border: 'none',
                                outline: 'none',
                                color: '#111827',
                                background: 'transparent'
                            }}
                        />
                        <PaintBucket size={16} color="#9ca3af" style={{ marginLeft: '10px' }} />
                        <input
                            type="color"
                            value={bgColor}
                            onChange={(e) => setBgColor(e.target.value)}
                            style={{ border: 'none', background: 'none', width: '24px', height: '24px', cursor: 'pointer' }}
                        />
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                        onClick={generateAiLayout}
                        className="btn"
                        style={{
                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            color: 'white',
                            border: 'none',
                            display: 'flex',
                            gap: '8px',
                            alignItems: 'center',
                            boxShadow: '0 2px 4px rgba(99, 102, 241, 0.3)'
                        }}
                    >
                        <Sparkles size={18} /> AI Agent Layout
                    </button>

                    <button
                        onClick={handlePublish}
                        className="btn btn-primary"
                        style={{ display: 'flex', gap: '8px', alignItems: 'center' }}
                    >
                        <MonitorPlay size={18} /> Publish & View
                    </button>
                </div>
            </div>

            <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                {/* Canvas Area */}
                <div style={{ flex: 1, overflow: 'auto', padding: '20px', background: bgColor }}>
                    <div style={{
                        minHeight: '1000px',
                        background: 'rgba(0,0,0,0.02)',
                        borderRadius: '12px',
                        border: '2px dashed #e5e7eb',
                        position: 'relative'
                    }}>
                        {layout.length === 0 && (
                            <div style={{
                                position: 'absolute',
                                top: '50%',
                                left: '50%',
                                transform: 'translate(-50%, -50%)',
                                textAlign: 'center',
                                color: '#9ca3af',
                                pointerEvents: 'none'
                            }}>
                                <Layout size={48} style={{ margin: '0 auto 10px', opacity: 0.5 }} />
                                <h3 style={{ fontSize: '1.2rem', fontWeight: '600' }}>Start Building Your Dashboard</h3>
                                <p>Drag charts from the sidebar or use the AI Agent.</p>
                            </div>
                        )}

                        <ResponsiveGridLayout
                            className="layout"
                            layouts={{ lg: layout, md: layout, sm: layout, xs: layout, xxs: layout }}
                            breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                            cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
                            rowHeight={30}
                            width={1200}
                            isDroppable={true}
                            onDrop={onDrop}
                            onLayoutChange={(currentLayout) => setLayout(currentLayout)}
                            draggableHandle=".drag-handle"
                        >
                            {layout.map(item => {
                                // Find chart title/metadata for this item ID
                                let chartTitle = "Unknown Chart";
                                // Search in all categories
                                for (const cat in charts) {
                                    const found = charts[cat].find(c => c.path === item.i);
                                    if (found) chartTitle = found.title;
                                }
                                if (customTitles[item.i]) chartTitle = customTitles[item.i];

                                return (
                                    <div key={item.i} style={{
                                        background: 'white',
                                        borderRadius: '8px',
                                        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                                        overflow: 'hidden',
                                        display: 'flex',
                                        flexDirection: 'column'
                                    }}>
                                        <div className="drag-handle" style={{
                                            padding: '8px 12px',
                                            background: '#f8fafc',
                                            borderBottom: '1px solid #f1f5f9',
                                            cursor: 'move',
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center'
                                        }}>
                                            <span
                                                onDoubleClick={() => {
                                                    const newTitle = prompt("Rename Chart:", chartTitle);
                                                    if (newTitle) setCustomTitles(prev => ({ ...prev, [item.i]: newTitle }));
                                                }}
                                                style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#475569', cursor: 'text' }}
                                            >
                                                {chartTitle}
                                            </span>
                                            <div onClick={() => setLayout(layout.filter(l => l.i !== item.i))} style={{ cursor: 'pointer', color: '#cbd5e1' }}>
                                                <X size={14} />
                                            </div>
                                        </div>
                                        <div style={{ flex: 1, padding: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                                            <img
                                                src={`/static/charts/${jobId}/${item.i}`}
                                                alt={chartTitle}
                                                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', pointerEvents: 'none' }}
                                            />
                                        </div>
                                    </div>
                                );
                            })}
                        </ResponsiveGridLayout>
                    </div>
                </div>

                {/* Sidebar */}
                <div style={{
                    width: '300px',
                    background: 'white',
                    borderLeft: '1px solid #e5e7eb',
                    display: 'flex',
                    flexDirection: 'column',
                    zIndex: 20
                }}>
                    <div style={{ padding: '15px', borderBottom: '1px solid #f3f4f6', fontWeight: 'bold', color: '#111827' }}>
                        Visual Gallery
                    </div>
                    <div style={{ flex: 1, overflowY: 'auto', padding: '15px' }}>
                        {Object.entries(charts).map(([category, items]) => (
                            <div key={category} style={{ marginBottom: '20px' }}>
                                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#9ca3af', marginBottom: '10px', letterSpacing: '0.05em' }}>
                                    {category}
                                </div>
                                {items && items.map(renderSidebarItem)}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ReportBuilder;
