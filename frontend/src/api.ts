/**
 * API configuration and base URL
 */

// Base URL for the Flask backend
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

// API endpoints
export const API_ENDPOINTS = {
  clients: `${API_BASE_URL}/clients`,
  invoices: `${API_BASE_URL}/invoices`,
  analytics: {
    monthly: `${API_BASE_URL}/analytics/monthly`,
    topClients: `${API_BASE_URL}/analytics/top_clients`,
    aging: `${API_BASE_URL}/analytics/aging`,
  },
  import: `${API_BASE_URL}/import/csv`,
  backup: `${API_BASE_URL}/backup`,
  restore: `${API_BASE_URL}/restore`,
};

// Types
export interface Client {
  id: number;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  tax_id?: string;
  default_tax_rate: number;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface InvoiceItem {
  id?: number;
  invoice_id?: number;
  description: string;
  quantity: number;
  rate: number;
  amount: number;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  client_id: number;
  client_name?: string;
  invoice_date: string;
  due_date?: string;
  short_desc?: string;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  total: number;
  status: 'draft' | 'sent' | 'paid' | 'void';
  paid_date?: string;
  notes?: string;
  signature_path?: string;
  items?: InvoiceItem[];
  created_at?: string;
  updated_at?: string;
}

export interface MonthlyRevenue {
  month: string;
  revenue: number;
  invoice_count: number;
}

export interface TopClient {
  client_name: string;
  total_revenue: number;
  invoice_count: number;
  avg_invoice: number;
}

export interface AgingBuckets {
  bucket_0_30: number;
  bucket_31_60: number;
  bucket_61_plus: number;
  total_unpaid: number;
}

// Fetch wrapper with error handling
export async function fetchAPI<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// API functions
export const api = {
  // Clients
  getClients: (search?: string) => {
    const url = search ? `${API_ENDPOINTS.clients}?search=${encodeURIComponent(search)}` : API_ENDPOINTS.clients;
    return fetchAPI<Client[]>(url);
  },
  
  getClient: (id: number) => fetchAPI<Client>(`${API_ENDPOINTS.clients}/${id}`),
  
  createClient: (data: Partial<Client>) =>
    fetchAPI<Client>(API_ENDPOINTS.clients, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  updateClient: (id: number, data: Partial<Client>) =>
    fetchAPI<Client>(`${API_ENDPOINTS.clients}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  deleteClient: (id: number) =>
    fetchAPI<{ message: string }>(`${API_ENDPOINTS.clients}/${id}`, {
      method: 'DELETE',
    }),

  // Invoices
  getInvoices: (filters?: {
    client_id?: number;
    status?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }
    const url = params.toString() ? `${API_ENDPOINTS.invoices}?${params}` : API_ENDPOINTS.invoices;
    return fetchAPI<Invoice[]>(url);
  },
  
  getInvoice: (id: number) => fetchAPI<Invoice>(`${API_ENDPOINTS.invoices}/${id}`),
  
  createInvoice: (data: Partial<Invoice>) =>
    fetchAPI<Invoice>(API_ENDPOINTS.invoices, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  updateInvoice: (id: number, data: Partial<Invoice>) =>
    fetchAPI<Invoice>(`${API_ENDPOINTS.invoices}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  markInvoicePaid: (id: number, paidDate?: string) =>
    fetchAPI<Invoice>(`${API_ENDPOINTS.invoices}/${id}/mark_paid`, {
      method: 'POST',
      body: JSON.stringify({ paid_date: paidDate }),
    }),
  
  generatePDF: async (id: number): Promise<Blob> => {
    const response = await fetch(`${API_ENDPOINTS.invoices}/${id}/generate_pdf`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to generate PDF');
    }
    return await response.blob();
  },

  // Analytics
  getMonthlyRevenue: (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    const url = params.toString() ? `${API_ENDPOINTS.analytics.monthly}?${params}` : API_ENDPOINTS.analytics.monthly;
    return fetchAPI<MonthlyRevenue[]>(url);
  },
  
  getTopClients: (limit = 5) =>
    fetchAPI<TopClient[]>(`${API_ENDPOINTS.analytics.topClients}?limit=${limit}`),
  
  getAgingBuckets: () => fetchAPI<AgingBuckets>(API_ENDPOINTS.analytics.aging),
};
