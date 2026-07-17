/**
 * NGO Volunteer Management System — API Client
 * Boilerplate: Axios-based API helper (to be extended in the UI phase).
 */

const API_BASE = "/api";

const getToken = () => localStorage.getItem("access_token");

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Attach token to every request
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers["Authorization"] = `Bearer ${token}`;
  return config;
});

// Global response error handler
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalConfig = err.config;
    
    // If we get a 401 and we haven't already retried
    if (err.response?.status === 401 && !originalConfig._retry) {
      originalConfig._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");
      
      if (refreshToken) {
        try {
          const rs = await axios.post("/api/auth/refresh", { refresh_token: refreshToken });
          
          if (rs.data?.status === "success" && rs.data?.data?.access_token) {
            localStorage.setItem("access_token", rs.data.data.access_token);
            originalConfig.headers["Authorization"] = `Bearer ${rs.data.data.access_token}`;
            return api(originalConfig); // Retry original request
          }
        } catch (_error) {
          // Refresh failed (expired or blacklisted)
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      } else {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }
    
    return Promise.reject(err);
  }
);
