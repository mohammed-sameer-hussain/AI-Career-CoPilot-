import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE}/auth/token/refresh/`, {
          refresh: refreshToken,
        });
        const { access } = response.data;
        localStorage.setItem('access_token', access);
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);
      } catch (e) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const apiService = {
  profiles: {
    list: () => api.get('/profiles/'),
    create: (data) => api.post('/profiles/', data),
    get: (id) => api.get(`/profiles/${id}/`),
    update: (id, data) => api.patch(`/profiles/${id}/`, data),
    delete: (id) => api.delete(`/profiles/${id}/`),
  },
  resumes: {
    list: () => api.get('/resumes/'),
    upload: (profileId, file) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('profile', profileId);
      return api.post('/resumes/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    get: (id) => api.get(`/resumes/${id}/`),
    delete: (id) => api.delete(`/resumes/${id}/`),
  },
  jobs: {
    list: (params) => api.get('/jobs/', { params }),
    get: (id) => api.get(`/jobs/${id}/`),
    scan: (profileId) => api.post('/jobs/scan/', { profile_id: profileId }),
    getMatch: (jobId) => api.get(`/jobs/${jobId}/match/`),
    match: (jobId, profileId) => api.post(`/jobs/${jobId}/match/`, { profile_id: profileId }),
    matchAll: (minScore) => api.post('/jobs/match-all/', { min_score: minScore || 0 }),
    application: (jobId, profileId) => api.post(`/jobs/${jobId}/application/`, { profile_id: profileId }),
    skillGapPlan: (jobId) => api.post(`/jobs/${jobId}/skill-gap-plan/`),
  },
  applications: {
    list: (params) => api.get('/applications/', { params }),
    get: (id) => api.get(`/applications/${id}/`),
    update: (id, data) => api.patch(`/applications/${id}/`, data),
  },
  notifications: {
    list: (params) => api.get('/notifications/', { params }),
    markRead: (id) => api.patch(`/notifications/${id}/`, { read: true }),
    markAllRead: () => api.post('/notifications/mark-all-read/'),
  },
  assistant: {
    history: (params) => api.get('/assistant/', { params }),
    send: (message, jobId) => api.post('/assistant/', { message, job: jobId }),
    clear: () => api.delete('/assistant/clear/'),
  },
  dashboard: {
    get: () => api.get('/dashboard/'),
  },
  auth: {
    login: (email, password) => api.post('/auth/login/', { email, password }),
    register: (data) => api.post('/auth/register/', data),
    refresh: (refreshToken) => api.post('/auth/token/refresh/', { refresh: refreshToken }),
  },
};

export default api;