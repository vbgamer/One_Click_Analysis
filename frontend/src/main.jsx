import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import './styles/intelligence.css'
import App from './App.jsx'


// === DEBUG: Global error handler to catch uncaught errors ===
window.onerror = function (message, source, lineno, colno, error) {
  const errorDiv = document.createElement('div');
  errorDiv.style.cssText = 'position:fixed;top:0;left:0;right:0;background:red;color:white;padding:20px;z-index:99999;font-family:monospace;';
  errorDiv.innerHTML = `<strong>GLOBAL ERROR:</strong> ${message}<br>Source: ${source}:${lineno}:${colno}<br><pre>${error?.stack || 'No stack'}</pre>`;
  document.body.prepend(errorDiv);
  return false;
};

window.onunhandledrejection = function (event) {
  const errorDiv = document.createElement('div');
  errorDiv.style.cssText = 'position:fixed;top:0;left:0;right:0;background:orange;color:black;padding:20px;z-index:99999;font-family:monospace;';
  errorDiv.innerHTML = `<strong>UNHANDLED PROMISE REJECTION:</strong> ${event.reason}`;
  document.body.prepend(errorDiv);
};

console.log("=== MAIN SCRIPT EXECUTING ===");

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("React Error Boundary Caught:", error, errorInfo);
    this.setState({ errorInfo });
    // Also show an alert for visibility
    alert("React Error: " + error.toString());
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, color: 'red', fontFamily: 'monospace', background: '#1a1a1a', minHeight: '100vh' }}>
          <h1>Something went wrong.</h1>
          <details open>
            <summary>Error Details</summary>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{this.state.error && this.state.error.toString()}</pre>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{this.state.errorInfo && this.state.errorInfo.componentStack}</pre>
          </details>
        </div>
      );
    }
    return this.props.children;
  }
}

try {
  console.log("=== ATTEMPTING TO RENDER APP ===");
  const rootElement = document.getElementById('root');
  console.log("Root element:", rootElement);

  if (!rootElement) {
    throw new Error("Root element not found!");
  }

  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>
  );
  console.log("=== RENDER CALL COMPLETED ===");
} catch (err) {
  console.error("=== RENDER FAILED ===", err);
  document.body.innerHTML = `<div style="padding:20px;color:red;font-family:monospace;background:#1a1a1a;min-height:100vh;"><h1>RENDER FAILED</h1><pre>${err.stack}</pre></div>`;
}
