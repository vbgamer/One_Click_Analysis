import axios from 'axios';
import safeStorage from './utils/storage';

// In dev, call the local FastAPI server on :8000.
// In production, default to same-origin so PythonAnywhere can serve the React
// build and API from one domain without an exposed :8000 port.
const backendHost = window.location.hostname;  // e.g. 'localhost' or '192.168.0.103'
const isDev = import.meta.env.DEV;
const backendURL = import.meta.env.VITE_API_URL || (isDev ? `http://${backendHost}:8000` : '');

const api = axios.create({
    baseURL: backendURL,
});

// Attach JWT token to every request
api.interceptors.request.use(
    (config) => {
        const token = safeStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);


// Global response interceptor: handle 402 (out of credits)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 402) {
            // Dispatch a custom event that CreditModal listens to
            window.dispatchEvent(new CustomEvent('credits:insufficient', {
                detail: { message: error.response.data?.detail }
            }));
        }
        return Promise.reject(error);
    }
);

export default api;
