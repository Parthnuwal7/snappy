import axios, { InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // Use admin token only for admin routes
  if (config.url?.includes('/admin/')) {
    const adminToken = localStorage.getItem('snappy_admin_token');
    if (adminToken && config.headers) {
      config.headers.Authorization = `Bearer ${adminToken}`;
    }
  } else {
    // Use user token for all other routes
    const userToken = localStorage.getItem('snappy_token');
    if (userToken && config.headers) {
      config.headers.Authorization = `Bearer ${userToken}`;
    }
  }
  return config;
});

// Auth API
export const authAPI = {
  register: (data: any) => api.post('/auth/register', data),
  login: (email: string, password: string) => api.post('/auth/login', { email, password }),
  getMe: () => api.get('/auth/me'),
};

// Payment API
export const paymentAPI = {
  // UPI Payment Methods (Active)
  getUPIDetails: (plan: string) => api.get(`/payment/upi-details/${plan}`),
  submitUPIPayment: (plan: string, upiTransactionId: string) => 
    api.post('/payment/submit-upi', { plan, upiTransactionId }),
  
  // Razorpay Methods (Commented - kept for reference)
  // createOrder: (plan: string) => api.post('/payment/create-order', { plan }),
  // verifyPayment: (data: any) => api.post('/payment/verify', data),
};

// Admin API
export const adminAPI = {
  getPendingLicenses: () => api.get('/admin/pending-licenses'),
  getAllLicenses: () => api.get('/admin/all-licenses'),
  verifyPayment: (licenseId: number, notes?: string) => 
    api.post(`/admin/verify-payment/${licenseId}`, { notes }),
  sendLicenseEmail: (licenseId: number) => 
    api.post(`/admin/send-license-email/${licenseId}`),
  rejectPayment: (licenseId: number, reason?: string) => 
    api.post(`/admin/reject-payment/${licenseId}`, { reason }),
};

// License API
export const licenseAPI = {
  getLicenses: () => api.get('/licenses'),
  getLicense: (id: number) => api.get(`/licenses/${id}`),
};

// Dashboard API
export const dashboardAPI = {
  getDashboard: () => api.get('/dashboard'),
};

export default api;
