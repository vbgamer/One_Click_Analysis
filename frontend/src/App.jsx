import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Status from './pages/Status';
import ReportView from './pages/ReportView';
import History from './pages/History';
import Settings from './pages/Settings';

import Landing from './pages/Landing';
import ChartSelection from './pages/ChartSelection';
import LayoutBuilder from './pages/LayoutBuilder';

function App() {
  const isAuthenticated = !!localStorage.getItem('token'); // Basic auth check

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />

        {/* Customize Report Flow (outside Layout for full-screen) */}
        <Route path="/builder/:jobId" element={<ChartSelection />} />
        <Route path="/builder/:jobId/layout" element={<LayoutBuilder />} />

        {/* Protected Routes */}
        <Route element={<Layout />}>
          {/* Note: We removed the auto-redirect from / to /dashboard so landing works for everyone.
              Users can click 'Login' on landing to go to dashboard if auth. */}
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/status/:jobId" element={<Status />} />
          <Route path="/report/:jobId" element={<ReportView />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

