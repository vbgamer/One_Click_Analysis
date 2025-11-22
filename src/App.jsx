import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import UploadZone from './components/UploadZone';
import ReportViewer from './components/ReportViewer';
import ReportsPage from './components/ReportsPage';
import Auth from './components/Auth';


export default function App(){
const [user, setUser] = useState(() => localStorage.getItem('oca_user') || null);
const [theme, setTheme] = useState(() => localStorage.getItem('oca_theme') || 'light');
const navigate = useNavigate();


useEffect(()=>{
document.documentElement.setAttribute('data-theme', theme);
localStorage.setItem('oca_theme', theme);
},[theme]);


return (
<div className="app-container">
<Sidebar />
<div className="main-content">
<Header user={user} setUser={setUser} theme={theme} setTheme={setTheme} />
<div className="page-body">
<Routes>
<Route path="/" element={<UploadZone />} />
<Route path="/reports" element={<ReportsPage />} />
<Route path="/report/:jobId" element={<ReportViewer />} />
<Route path="/login" element={<Auth onLogin={(u)=>{ setUser(u); localStorage.setItem('oca_user', u); navigate('/'); }} />} />
</Routes>
</div>
</div>
</div>
);
}
