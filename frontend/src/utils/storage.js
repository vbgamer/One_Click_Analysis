// Robust, crash-proof wrapper for localStorage that falls back to in-memory storage 
// if localStorage is blocked by browser security settings (e.g., third-party cookies disabled, or incognito mode).

const memoryStorage = {};

const safeStorage = {
    getItem(key) {
        try {
            return window.localStorage.getItem(key);
        } catch (e) {
            console.warn(`localStorage.getItem failed for key "${key}":`, e);
            return memoryStorage[key] || null;
        }
    },
    setItem(key, value) {
        try {
            window.localStorage.setItem(key, value);
        } catch (e) {
            console.warn(`localStorage.setItem failed for key "${key}":`, e);
            memoryStorage[key] = String(value);
        }
    },
    removeItem(key) {
        try {
            window.localStorage.removeItem(key);
        } catch (e) {
            console.warn(`localStorage.removeItem failed for key "${key}":`, e);
            delete memoryStorage[key];
        }
    },
    clear() {
        try {
            window.localStorage.clear();
        } catch (e) {
            console.warn("localStorage.clear failed:", e);
            Object.keys(memoryStorage).forEach(key => delete memoryStorage[key]);
        }
    }
};

export default safeStorage;
