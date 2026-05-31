import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Status from './pages/Status';
import ReportView from './pages/ReportView';
import History from './pages/History';
import Settings from './pages/Settings';
import AdminDashboard from './pages/AdminDashboard';
import Landing from './pages/Landing';
import ChartSelection from './pages/ChartSelection';
import LayoutBuilder from './pages/LayoutBuilder';
import Intelligence from './pages/Intelligence';
import ConversationalAI from './pages/ConversationalAI';
import safeStorage from './utils/storage';

function App() {
  const isAuthenticated = !!safeStorage.getItem('token');

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />

        {/* AI Intelligence (full-screen, outside layout) */}
        <Route path="/intelligence/:jobId" element={<Intelligence />} />
        <Route path="/chat/:jobId" element={<ConversationalAI />} />

        {/* Customize Report Flow (full-screen) */}
        <Route path="/builder/:jobId" element={<ChartSelection />} />
        <Route path="/builder/:jobId/layout" element={<LayoutBuilder />} />

        {/* Protected Routes */}
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/status/:jobId" element={<Status />} />
          <Route path="/report/:jobId" element={<ReportView />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
