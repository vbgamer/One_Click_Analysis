import axios from 'axios';
import safeStorage from './utils/storage';

// Prefer same-origin API calls.
//
// Development: Vite proxies these paths to FastAPI. This avoids browser/CORS
// failures when the UI is opened through localhost, 127.0.0.1, or a LAN/IP URL.
// Production: FastAPI serves the Vite build and API from the same domain.
//
// Set VITE_API_URL only when the API is intentionally hosted on another domain.
const backendURL = import.meta.env.VITE_API_URL || '';

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
