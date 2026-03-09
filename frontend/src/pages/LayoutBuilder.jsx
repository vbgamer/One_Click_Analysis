import React, { useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Download, ArrowLeft, Plus, Trash2, GripVertical, FileText, Edit2, Check, X, Palette, Settings, ArrowUpDown, Filter, Paintbrush } from 'lucide-react';
import FormattingPanel from '../components/ReportBuilder/FormattingPanel';
import SortingPanel from '../components/ReportBuilder/SortingPanel';
import FilterPanel from '../components/ReportBuilder/FilterPanel';
import ThemeManager from '../components/ReportBuilder/ThemeManager';

const LayoutBuilder = () => {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const printRef = useRef(null);

    // Get selected charts from navigation state
    const selectedCharts = location.state?.selectedCharts || [];

    // Multi-page state: each page has charts with size info
    // Chart object: { path, title, category, customTitle, width, height, titleColor, bgColor }
    const [pages, setPages] = useState([{ id: 1, charts: [] }]);
    const [currentPage, setCurrentPage] = useState(0);
    const [draggedChart, setDraggedChart] = useState(null);
    const [editingChart, setEditingChart] = useState(null);
    const [editTitle, setEditTitle] = useState('');

    // Dashboard customization
    const [dashboardName, setDashboardName] = useState('Custom Dashboard');
    const [dashboardBgColor, setDashboardBgColor] = useState('#f1f5f9');
    const [editingDashboardName, setEditingDashboardName] = useState(false);
    const [dashboardTheme, setDashboardTheme] = useState(null);

    // Panel visibility states
    const [selectedChartForFormatting, setSelectedChartForFormatting] = useState(null);
    const [showSortPanel, setShowSortPanel] = useState(false);
    const [showFilterPanel, setShowFilterPanel] = useState(false);
    const [showThemeManager, setShowThemeManager] = useState(false);
    const [sortingChart, setSortingChart] = useState(null);
    const [filteringChart, setFilteringChart] = useState(null);

    // Available charts (not yet placed on any page)
    const getAvailableCharts = () => {
        const placedPaths = pages.flatMap(p => p.charts.map(c => c.path));
        return selectedCharts.filter(c => !placedPaths.includes(c.path));
    };

    // Drag handlers
    const handleDragStart = (e, chart) => {
        setDraggedChart(chart);
        e.dataTransfer.effectAllowed = 'move';
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    };

    const handleDrop = (e) => {
        e.preventDefault();
        if (!draggedChart) return;

        setPages(prev => {
            const newPages = [...prev];
            const pageCharts = newPages[currentPage].charts;

            // Check if already on this page
            if (!pageCharts.find(c => c.path === draggedChart.path)) {
                const chartWithSize = {
                    ...draggedChart,
                    customTitle: draggedChart.title,
                    width: 'half',  // 'half', 'full', 'quarter'
                    height: 250,
                    titleColor: '#1e293b',  // Default dark color
                    bgColor: '#ffffff'  // Default white background
                };
                newPages[currentPage] = {
                    ...newPages[currentPage],
                    charts: [...pageCharts, chartWithSize]
                };
            }
            return newPages;
        });
        setDraggedChart(null);
    };

    const removeChartFromPage = (chartPath) => {
        setPages(prev => {
            const newPages = [...prev];
            newPages[currentPage] = {
                ...newPages[currentPage],
                charts: newPages[currentPage].charts.filter(c => c.path !== chartPath)
            };
            return newPages;
        });
    };

    // Resize chart
    const resizeChart = (chartPath, newWidth) => {
        setPages(prev => {
            const newPages = [...prev];
            newPages[currentPage] = {
                ...newPages[currentPage],
                charts: newPages[currentPage].charts.map(c =>
                    c.path === chartPath ? { ...c, width: newWidth } : c
                )
            };
            return newPages;
        });
    };

    // Update chart height
    const updateChartHeight = (chartPath, newHeight) => {
        setPages(prev => {
            const newPages = [...prev];
            newPages[currentPage] = {
                ...newPages[currentPage],
                charts: newPages[currentPage].charts.map(c =>
                    c.path === chartPath ? { ...c, height: newHeight } : c
                )
            };
            return newPages;
        });
    };

    // Update title color
    const updateTitleColor = (chartPath, newColor) => {
        setPages(prev => {
            const newPages = [...prev];
            newPages[currentPage] = {
                ...newPages[currentPage],
                charts: newPages[currentPage].charts.map(c =>
                    c.path === chartPath ? { ...c, titleColor: newColor } : c
                )
            };
            return newPages;
        });
    };

    // Update chart background color
    const updateChartBgColor = (chartPath, newColor) => {
        setPages(prev => {
            const newPages = [...prev];
            newPages[currentPage] = {
                ...newPages[currentPage],
                charts: newPages[currentPage].charts.map(c =>
                    c.path === chartPath ? { ...c, bgColor: newColor } : c
                )
            };
            return newPages;
        });
    };

    // Update chart with formatting changes
    const updateChartFormatting = (updatedChart) => {
        setPages(prev => {
            const newPages = [...prev];
            newPages[currentPage] = {
                ...newPages[currentPage],
                charts: newPages[currentPage].charts.map(c =>
                    c.path === updatedChart.path ? updatedChart : c
                )
            };
            return newPages;
        });
        setSelectedChartForFormatting(updatedChart);
    };

    // Rename chart
    const startRename = (chart) => {
        setEditingChart(chart.path);
        setEditTitle(chart.customTitle || chart.title);
    };

    const saveRename = (chartPath) => {
        setPages(prev => {
            const newPages = [...prev];
            newPages[currentPage] = {
                ...newPages[currentPage],
                charts: newPages[currentPage].charts.map(c =>
                    c.path === chartPath ? { ...c, customTitle: editTitle } : c
                )
            };
            return newPages;
        });
        setEditingChart(null);
        setEditTitle('');
    };

    const cancelRename = () => {
        setEditingChart(null);
        setEditTitle('');
    };

    const addNewPage = () => {
        const newId = Math.max(...pages.map(p => p.id)) + 1;
        setPages(prev => [...prev, { id: newId, charts: [] }]);
        setCurrentPage(pages.length);
    };

    const deletePage = (pageIndex) => {
        if (pages.length === 1) {
            alert("You must have at least one page.");
            return;
        }
        setPages(prev => prev.filter((_, i) => i !== pageIndex));
        if (currentPage >= pageIndex && currentPage > 0) {
            setCurrentPage(currentPage - 1);
        }
    };

    const getWidthStyle = (width) => {
        switch (width) {
            case 'full': return '100%';
            case 'half': return 'calc(50% - 0.75rem)';
            case 'quarter': return 'calc(25% - 1.125rem)';
            default: return 'calc(50% - 0.75rem)';
        }
    };

    const handleDownload = () => {
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${dashboardName}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: ${dashboardBgColor}; }
                    .dashboard-title { font-size: 28px; font-weight: bold; margin-bottom: 30px; color: #1e293b; text-align: center; }
                    .page { page-break-after: always; padding: 20px; margin-bottom: 20px; }
                    .page:last-child { page-break-after: avoid; }
                    .page-title { font-size: 20px; font-weight: bold; margin-bottom: 20px; color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
                    .charts-container { display: flex; flex-wrap: wrap; gap: 20px; }
                    .chart-item { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; box-sizing: border-box; }
                    .chart-item.full { width: 100%; }
                    .chart-item.half { width: calc(50% - 10px); }
                    .chart-item.quarter { width: calc(25% - 15px); }
                    .chart-title { font-weight: bold; margin-bottom: 10px; }
                    .chart-img { width: 100%; object-fit: contain; }
                    @media print {
                        .page { page-break-after: always; }
                        .page:last-child { page-break-after: avoid; }
                    }
                </style>
            </head>
            <body>
                <div class="dashboard-title">${dashboardName}</div>
                ${pages.map((page, idx) => `
                    <div class="page">
                        <div class="page-title">Page ${idx + 1}</div>
                        <div class="charts-container">
                            ${page.charts.map(chart => `
                                <div class="chart-item ${chart.width}" style="background: ${chart.bgColor || '#ffffff'}">
                                    <div class="chart-title" style="color: ${chart.titleColor || '#475569'}">${chart.customTitle || chart.title}</div>
                                    <img class="chart-img" style="max-height: ${chart.height}px" src="${window.location.origin}/static/charts/${jobId}/${chart.path}" alt="${chart.customTitle || chart.title}" />
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </body>
            </html>
        `);
        printWindow.document.close();
        setTimeout(() => {
            printWindow.print();
        }, 500);
    };

    const availableCharts = getAvailableCharts();
    const currentPageData = pages[currentPage];

    if (selectedCharts.length === 0) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                background: 'var(--background)',
                color: 'var(--text-primary)'
            }}>
                <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                    <p>No charts selected. Please go back and select charts first.</p>
                    <button onClick={() => navigate(`/builder/${jobId}`)} className="btn btn-primary" style={{ marginTop: '1rem' }}>
                        Go Back
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--background)',
            color: 'var(--text-primary)'
        }}>
            {/* Header */}
            <div style={{
                padding: '1rem 2rem',
                background: 'var(--bg-card)',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <button onClick={() => navigate(-1)} className="btn btn-outline" style={{ padding: '0.5rem' }}>
                        <ArrowLeft size={20} />
                    </button>

                    {/* Editable Dashboard Name */}
                    {editingDashboardName ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <input
                                type="text"
                                value={dashboardName}
                                onChange={(e) => setDashboardName(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && setEditingDashboardName(false)}
                                autoFocus
                                style={{
                                    fontSize: '1.5rem',
                                    fontWeight: 'bold',
                                    padding: '0.25rem 0.5rem',
                                    border: '1px solid var(--primary)',
                                    borderRadius: '4px',
                                    outline: 'none',
                                    width: '250px'
                                }}
                            />
                            <button onClick={() => setEditingDashboardName(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--success)' }}>
                                <Check size={20} />
                            </button>
                        </div>
                    ) : (
                        <h1
                            style={{ fontSize: '1.5rem', fontWeight: 'bold', cursor: 'pointer' }}
                            onDoubleClick={() => setEditingDashboardName(true)}
                            title="Double-click to rename"
                        >
                            {dashboardName}
                        </h1>
                    )}
                    <button
                        onClick={() => setEditingDashboardName(true)}
                        style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
                        title="Rename dashboard"
                    >
                        <Edit2 size={16} />
                    </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    {/* Theme Button */}
                    <button
                        onClick={() => setShowThemeManager(true)}
                        style={{
                            padding: '0.5rem 1rem',
                            background: 'transparent',
                            border: '1px solid var(--border)',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            color: 'var(--text-secondary)'
                        }}
                        title="Report Theme"
                    >
                        <Paintbrush size={16} />
                        <span style={{ fontSize: '0.85rem' }}>Theme</span>
                    </button>

                    {/* Dashboard Background Color */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Background:</span>
                        <input
                            type="color"
                            value={dashboardBgColor}
                            onChange={(e) => setDashboardBgColor(e.target.value)}
                            title="Dashboard background color"
                            style={{
                                width: '32px',
                                height: '32px',
                                padding: 0,
                                border: '1px solid var(--border)',
                                borderRadius: '6px',
                                cursor: 'pointer'
                            }}
                        />
                    </div>

                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={handleDownload}
                        className="btn btn-primary"
                        style={{
                            padding: '0.75rem 1.5rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            background: '#dc2626'
                        }}
                    >
                        <Download size={18} />
                        Download PDF
                    </motion.button>
                </div>
            </div>

            <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                {/* Left Sidebar - Available Charts */}
                <div style={{
                    width: '280px',
                    background: 'var(--bg-card)',
                    borderRight: '1px solid var(--border)',
                    display: 'flex',
                    flexDirection: 'column'
                }}>
                    <div style={{
                        padding: '1rem',
                        borderBottom: '1px solid var(--border)',
                        fontWeight: 'bold'
                    }}>
                        Available Charts ({availableCharts.length})
                    </div>
                    <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
                        {availableCharts.length === 0 ? (
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', textAlign: 'center' }}>
                                All charts have been placed
                            </p>
                        ) : (
                            availableCharts.map(chart => (
                                <div
                                    key={chart.path}
                                    draggable
                                    onDragStart={(e) => handleDragStart(e, chart)}
                                    style={{
                                        padding: '0.75rem',
                                        background: '#f8fafc',
                                        border: '1px solid var(--border)',
                                        borderRadius: '8px',
                                        marginBottom: '0.75rem',
                                        cursor: 'grab',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.75rem'
                                    }}
                                >
                                    <GripVertical size={16} color="var(--text-secondary)" />
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontSize: '0.85rem', fontWeight: '500' }}>{chart.title}</div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{chart.category}</div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Main Canvas */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    {/* Page Tabs */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.75rem 1rem',
                        background: 'var(--bg-card)',
                        borderBottom: '1px solid var(--border)'
                    }}>
                        {pages.map((page, idx) => (
                            <div
                                key={page.id}
                                onClick={() => setCurrentPage(idx)}
                                style={{
                                    padding: '0.5rem 1rem',
                                    background: currentPage === idx ? 'var(--primary)' : 'transparent',
                                    color: currentPage === idx ? 'white' : 'var(--text-primary)',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    fontSize: '0.9rem'
                                }}
                            >
                                <FileText size={14} />
                                Page {idx + 1}
                                {pages.length > 1 && (
                                    <span
                                        onClick={(e) => { e.stopPropagation(); deletePage(idx); }}
                                        style={{ marginLeft: '0.25rem', opacity: 0.7 }}
                                    >
                                        ×
                                    </span>
                                )}
                            </div>
                        ))}
                        <button
                            onClick={addNewPage}
                            style={{
                                padding: '0.5rem',
                                background: 'transparent',
                                border: '1px dashed var(--border)',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                color: 'var(--text-secondary)'
                            }}
                        >
                            <Plus size={16} />
                        </button>
                    </div>

                    {/* Drop Zone */}
                    <div
                        ref={printRef}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                        style={{
                            flex: 1,
                            padding: '2rem',
                            overflowY: 'auto',
                            background: dashboardBgColor
                        }}
                    >
                        {currentPageData.charts.length === 0 ? (
                            <div style={{
                                height: '100%',
                                border: '2px dashed var(--border)',
                                borderRadius: '12px',
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'center',
                                alignItems: 'center',
                                color: 'var(--text-secondary)'
                            }}>
                                <FileText size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                                <p style={{ fontSize: '1.1rem', fontWeight: '500' }}>Drop charts here</p>
                                <p style={{ fontSize: '0.9rem' }}>Drag charts from the left sidebar</p>
                            </div>
                        ) : (
                            <div style={{
                                display: 'flex',
                                flexWrap: 'wrap',
                                gap: '1.5rem'
                            }}>
                                {currentPageData.charts.map(chart => {
                                    const borderFormatting = chart.formatting?.border || {};
                                    const shadowFormatting = chart.formatting?.shadow || {};
                                    const bgTransparency = chart.formatting?.background?.transparency || 0;

                                    return (
                                        <div
                                            key={chart.path}
                                            onClick={() => setSelectedChartForFormatting(chart)}
                                            style={{
                                                width: getWidthStyle(chart.width),
                                                background: chart.bgColor || '#ffffff',
                                                opacity: 1 - (bgTransparency / 100),
                                                border: `${borderFormatting.width || 1}px solid ${borderFormatting.color || 'var(--border)'}`,
                                                borderRadius: `${borderFormatting.radius || 12}px`,
                                                overflow: 'hidden',
                                                boxShadow: shadowFormatting.enabled !== false
                                                    ? `0 ${shadowFormatting.blur || 4}px ${(shadowFormatting.blur || 4) * 2}px ${shadowFormatting.color || 'rgba(0,0,0,0.1)'}`
                                                    : 'none',
                                                resize: 'both',
                                                minWidth: '200px',
                                                minHeight: '200px',
                                                cursor: 'pointer',
                                                outline: selectedChartForFormatting?.path === chart.path ? '2px solid var(--primary)' : 'none'
                                            }}
                                        >
                                            {/* Header with title and controls */}
                                            <div style={{
                                                padding: '0.75rem 1rem',
                                                background: '#f8fafc',
                                                borderBottom: '1px solid var(--border)',
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                gap: '0.5rem'
                                            }}>
                                                {editingChart === chart.path ? (
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1 }}>
                                                        <input
                                                            type="text"
                                                            value={editTitle}
                                                            onChange={(e) => setEditTitle(e.target.value)}
                                                            onKeyDown={(e) => e.key === 'Enter' && saveRename(chart.path)}
                                                            autoFocus
                                                            style={{
                                                                flex: 1,
                                                                padding: '0.25rem 0.5rem',
                                                                border: '1px solid var(--primary)',
                                                                borderRadius: '4px',
                                                                fontSize: '0.85rem',
                                                                outline: 'none'
                                                            }}
                                                        />
                                                        <button onClick={() => saveRename(chart.path)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--success)', padding: '0.25rem' }}>
                                                            <Check size={16} />
                                                        </button>
                                                        <button onClick={cancelRename} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--danger)', padding: '0.25rem' }}>
                                                            <X size={16} />
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <>
                                                        {chart.formatting?.title?.visible !== false && (
                                                            <span
                                                                style={{
                                                                    fontWeight: chart.formatting?.title?.fontWeight || '600',
                                                                    fontSize: `${chart.formatting?.title?.size || 14}px`,
                                                                    cursor: 'pointer',
                                                                    color: chart.titleColor || '#1e293b',
                                                                    textAlign: chart.formatting?.title?.alignment || 'left',
                                                                    flex: 1
                                                                }}
                                                                onDoubleClick={() => startRename(chart)}
                                                                title="Double-click to rename"
                                                            >
                                                                {chart.customTitle || chart.title}
                                                            </span>
                                                        )}
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                            <input
                                                                type="color"
                                                                value={chart.titleColor || '#1e293b'}
                                                                onChange={(e) => updateTitleColor(chart.path, e.target.value)}
                                                                title="Title color"
                                                                style={{
                                                                    width: '24px',
                                                                    height: '24px',
                                                                    padding: 0,
                                                                    border: '1px solid var(--border)',
                                                                    borderRadius: '4px',
                                                                    cursor: 'pointer',
                                                                    background: 'transparent'
                                                                }}
                                                            />
                                                            {/* Sort and Filter buttons removed - not applicable for static chart images */}
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); setSelectedChartForFormatting(chart); }}
                                                                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: selectedChartForFormatting?.path === chart.path ? 'var(--primary)' : 'var(--text-secondary)', padding: '0.25rem' }}
                                                                title="Format Visual"
                                                            >
                                                                <Settings size={14} />
                                                            </button>
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); startRename(chart); }}
                                                                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', padding: '0.25rem' }}
                                                                title="Rename"
                                                            >
                                                                <Edit2 size={14} />
                                                            </button>
                                                            <button
                                                                onClick={() => removeChartFromPage(chart.path)}
                                                                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--danger)', padding: '0.25rem' }}
                                                                title="Remove"
                                                            >
                                                                <Trash2 size={14} />
                                                            </button>
                                                        </div>
                                                    </>
                                                )}
                                            </div>

                                            {/* Size controls */}
                                            <div style={{
                                                padding: '0.5rem 1rem',
                                                background: '#f8fafc',
                                                borderBottom: '1px solid var(--border)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                fontSize: '0.75rem'
                                            }}>
                                                <span style={{ color: 'var(--text-secondary)' }}>Width:</span>
                                                {['quarter', 'half', 'full'].map(size => (
                                                    <button
                                                        key={size}
                                                        onClick={() => resizeChart(chart.path, size)}
                                                        style={{
                                                            padding: '0.25rem 0.5rem',
                                                            background: chart.width === size ? 'var(--primary)' : 'white',
                                                            color: chart.width === size ? 'white' : 'var(--text-primary)',
                                                            border: '1px solid var(--border)',
                                                            borderRadius: '4px',
                                                            cursor: 'pointer',
                                                            textTransform: 'capitalize',
                                                            fontSize: '0.7rem'
                                                        }}
                                                    >
                                                        {size === 'quarter' ? '25%' : size === 'half' ? '50%' : '100%'}
                                                    </button>
                                                ))}
                                                <span style={{ color: 'var(--text-secondary)', marginLeft: '1rem' }}>Height:</span>
                                                <input
                                                    type="range"
                                                    min="150"
                                                    max="500"
                                                    value={chart.height}
                                                    onChange={(e) => updateChartHeight(chart.path, parseInt(e.target.value))}
                                                    style={{ width: '80px' }}
                                                />
                                                <span style={{ color: 'var(--text-secondary)' }}>{chart.height}px</span>

                                                <span style={{ color: 'var(--text-secondary)', marginLeft: '1rem' }}>Chart BG:</span>
                                                <input
                                                    type="color"
                                                    value={chart.bgColor || '#ffffff'}
                                                    onChange={(e) => updateChartBgColor(chart.path, e.target.value)}
                                                    title="Chart background color"
                                                    style={{
                                                        width: '24px',
                                                        height: '24px',
                                                        padding: 0,
                                                        border: '1px solid var(--border)',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer'
                                                    }}
                                                />
                                            </div>

                                            {/* Chart image */}
                                            <div style={{
                                                padding: '1rem',
                                                display: 'flex',
                                                justifyContent: 'center',
                                                height: chart.height,
                                                overflow: 'hidden'
                                            }}>
                                                <img
                                                    src={`/static/charts/${jobId}/${chart.path}`}
                                                    alt={chart.customTitle || chart.title}
                                                    style={{
                                                        maxWidth: '100%',
                                                        maxHeight: '100%',
                                                        objectFit: 'contain'
                                                    }}
                                                />
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Formatting Panel */}
            {selectedChartForFormatting && (
                <FormattingPanel
                    chart={selectedChartForFormatting}
                    onUpdate={updateChartFormatting}
                    onClose={() => setSelectedChartForFormatting(null)}
                />
            )}

            {/* Sorting Panel Modal */}
            {sortingChart && (
                <SortingPanel
                    chart={sortingChart}
                    onUpdate={(updatedChart) => {
                        updateChartFormatting(updatedChart);
                        setSortingChart(updatedChart);
                    }}
                    onClose={() => setSortingChart(null)}
                />
            )}

            {/* Filter Panel Modal */}
            {filteringChart && (
                <FilterPanel
                    chart={filteringChart}
                    onUpdate={(updatedChart) => {
                        updateChartFormatting(updatedChart);
                        setFilteringChart(updatedChart);
                    }}
                    onClose={() => setFilteringChart(null)}
                />
            )}

            {/* Theme Manager Modal */}
            {showThemeManager && (
                <ThemeManager
                    currentTheme={dashboardTheme}
                    onApplyTheme={(theme) => {
                        setDashboardTheme(theme);
                        if (theme?.colors?.background) {
                            setDashboardBgColor(theme.colors.background);
                        }
                    }}
                    onClose={() => setShowThemeManager(false)}
                />
            )}
        </div>
    );
};

export default LayoutBuilder;
