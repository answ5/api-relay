import axios from 'axios';

const api = axios.create({
  baseURL: '/relay/api/admin',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.hash = '/login';
    }
    return Promise.reject(err);
  },
);

// ── Auth (works for both admin & user) ──
export function login(username, password) {
  return api.post('/auth/login', { username, password });
}
export function me() { return api.get('/auth/me'); }
export function logout() { return api.post('/auth/logout'); }

export function forgotPassword(data) { return api.post('/auth/forgot-password', data); }
export function resetPassword(data) { return api.post('/auth/reset-password', data); }

// ── User-facing API (uses auth JWT, not API key) ──
const userApi = axios.create({
  baseURL: '/relay/api/user',
});
userApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
userApi.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.hash = '/login';
    }
    return Promise.reject(err);
  },
);

export function userMe() { return userApi.get('/auth/me'); }
export function userProfile() { return userApi.get('/profile'); }
export function userUpdateProfile(data) { return userApi.put('/profile', data); }
export function userDashboardStats() { return userApi.get('/stats/dashboard'); }
export function userListTokens(params) { return userApi.get('/tokens', { params }); }
export function userCreateToken(data) { return userApi.post('/tokens', data); }
export function userDeleteToken(id) { return userApi.delete(`/tokens/${id}`); }
export function userRenameToken(id, data) { return userApi.put(`/tokens/${id}/name`, data); }
export function userListLogs(params) { return userApi.get('/logs', { params }); }
export function userListTransactions(params) { return userApi.get('/transactions', { params }); }
export function userLogsStats() { return userApi.get('/logs/stats'); }

// ── Admin API (protected, requires admin role) ──
export function listUsers(params) { return api.get('/users', { params }); }
export function createUser(data) { return api.post('/users', data); }
export function updateUser(id, data) { return api.put(`/users/${id}`, data); }
export function adjustBalance(id, data) { return api.post(`/users/${id}/balance`, data); }
export function adminResetUserPassword(id, data) { return api.put(`/users/${id}/password`, data); }

export function listTokens(params) { return api.get('/tokens', { params }); }
export function createToken(data) { return api.post('/tokens', data); }
export function updateToken(id, data) { return api.put(`/tokens/${id}`, data); }
export function deleteToken(id) { return api.delete(`/tokens/${id}`); }

export function listChannels(params) { return api.get('/channels', { params }); }
export function createChannel(data) { return api.post('/channels', data); }
export function updateChannel(id, data) { return api.put(`/channels/${id}`, data); }
export function healthCheckChannel(id) { return api.post(`/channels/${id}/health-check`); }

export function listModelPricing(params) { return api.get('/models', { params }); }
export function createModelPricing(data) { return api.post('/models', data); }
export function updateModelPricing(id, data) { return api.put(`/models/${id}`, data); }

export function listLogs(params) { return api.get('/logs', { params }); }
export function getLogPayload(id) { return api.get(`/logs/${id}/payload`); }
export function listTransactions(params) { return api.get('/transactions', { params }); }

export function dashboardStats() { return api.get('/stats/dashboard'); }
export function profitStats(params) { return api.get('/stats/profit', { params }); }

export default api;
