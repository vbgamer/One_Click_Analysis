import axios from 'axios';

// Auto-derive backend URL from the current host so it works on localhost AND LAN IP.
const backendHost = window.location.hostname;  // e.g. 'localhost' or '192.168.0.103'
const backendURL = import.meta.env.VITE_API_URL || `http://${backendHost}:8000`;

const api = axios.create({
    baseURL: backendURL,
});

// Attach JWT token to every request
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
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
