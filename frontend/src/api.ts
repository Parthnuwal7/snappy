/// <reference types="vite/client" />

/**
 * API configuration and base URL
 */

// Base URL for the Flask backend with API versioning
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1';

// API endpoints
export const API_ENDPOINTS = {
  // Auth endpoints
  auth: {
    login: `${API_BASE_URL}/auth/login`,
    register: `${API_BASE_URL}/auth/register`,
    logout: `${API_BASE_URL}/auth/logout`,
    me: `${API_BASE_URL}/auth/me`,
    onboard: `${API_BASE_URL}/auth/onboard`,
    deleteAccount: `${API_BASE_URL}/auth/delete_account`,
    // New JWT endpoints
    token: `${API_BASE_URL}/auth/token`,
    refresh: `${API_BASE_URL}/auth/refresh`,
    validate: `${API_BASE_URL}/auth/validate`,
  },
  // Core endpoints
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
  items: `${API_BASE_URL}/items`,
  recurring: `${API_BASE_URL}/recurring`,
  legalFeed: `${API_BASE_URL}/legal-feed`,
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

export interface Item {
  id: number;
  name: string;
  alias?: string;
  description?: string;
  default_rate: number;
  unit: string;
  hsn_code?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface LegalFeedItem {
  id: number;
  content_type: 'judgement' | 'news' | 'notice';
  title: string;
  summary?: string;
  source_url: string;
  source_name: string;
  court?: string;
  published_at?: string;
  ingested_at?: string;
  headline?: string | null;
  tldr?: string | null;
  topics?: string[];
  importance?: number | null;
  image_url?: string | null;
}

export const PRACTICE_AREAS = [
  'Tax', 'Criminal', 'Civil', 'Constitutional', 'Corporate/Commercial', 'IP',
  'Environment', 'Labour/Service', 'Family', 'Property', 'Banking/Insolvency',
  'Arbitration',
];

export interface LegalFeedPreference {
  topic_weights: Record<string, number>;
  courts: string[];
  interest_phrases: string[];
}

export interface Invoice {
  id: number;
  invoice_number: string;
  client_id: number;
  case_file_id?: number | null;
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
  sent_at?: string;
  sent_channel?: 'email' | 'whatsapp';
  notes?: string;
  items?: InvoiceItem[];
  upi_uri?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SendResult {
  channel: 'email' | 'whatsapp';
  whatsapp_url?: string;
  sent_to?: string;
  status: string;
  sent_at?: string;
  sent_channel?: string;
}

export interface PublicInvoice {
  invoice_number: string;
  invoice_date?: string;
  due_date?: string;
  status: string;
  short_desc?: string;
  subtotal?: number;
  tax_rate?: number;
  tax_amount?: number;
  total?: number;
  client_name?: string;
  items: InvoiceItem[];
  firm?: {
    firm_name?: string;
    firm_address?: string;
    firm_email?: string;
    firm_phone?: string;
    firm_website?: string;
  } | null;
  payment?: {
    upi_id?: string;
    bank_name?: string;
    account_number?: string;
    ifsc_code?: string;
    account_holder_name?: string;
    upi_uri?: string;
  } | null;
}

export interface RecurringSchedule {
  id: number;
  client_id: number;
  client_name?: string;
  title?: string;
  items: { description: string; quantity: number; rate: number }[];
  tax_rate: number;
  short_desc?: string;
  notes?: string;
  frequency: 'weekly' | 'monthly';
  start_date: string;
  next_run_date: string;
  end_date?: string;
  last_run_date?: string;
  active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Paginated<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
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

// ---- Firm tenancy & RBAC ---------------------------------------------------

export interface FirmTenant {
  id: number;
  name: string;
  created_at?: string;
}

export interface FirmRole {
  id: number;
  firm_id: number;
  name: string;
  description?: string | null;
  permissions: string[];
  is_system: boolean;
}

export interface FirmMember {
  id: number;
  email: string;
  role_id: number | null;
  role_name: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface FirmInvite {
  id: number;
  firm_id: number;
  email: string;
  role_id: number;
  status: 'pending' | 'accepted' | 'revoked' | 'expired';
  invited_by?: number | null;
  expires_at?: string | null;
  created_at?: string | null;
  accepted_at?: string | null;
}

export interface PermissionModule {
  key: string;
  label: string;
  actions: string[];
}

// ---- Case files (CRM spine) -----------------------------------------------

export interface CaseParty {
  id?: number;
  case_file_id?: number;
  name: string;
  role?: string;
}

export interface CaseFile {
  id: number;
  firm_id: number;
  created_by_user_id: number;
  case_number: string;
  title: string;
  client_id: number;
  client_name?: string;
  matter_type?: string;
  court?: string;
  court_case_number?: string;
  jurisdiction?: string;
  act_section?: string;
  opposing_counsel?: string;
  stage: string;
  priority: string;
  position: number;
  handling_advocate_user_id?: number | null;
  filing_date?: string | null;
  next_hearing_date?: string | null;
  open_date?: string | null;
  description?: string;
  agreed_fee?: number | null;
  parties?: CaseParty[];
  created_at?: string;
  updated_at?: string;
}

export interface CaseEvent {
  id: number;
  case_file_id: number;
  firm_id: number;
  created_by_user_id: number;
  event_date: string;
  kind: string;
  title: string;
  notes?: string | null;
  purpose?: string | null;
  outcome?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface CaseDocument {
  id: number;
  firm_id: number;
  case_file_id: number;
  event_id?: number | null;
  uploaded_by_user_id: number;
  title: string;
  doc_type: string;
  file_name?: string;
  mime_type?: string;
  size_bytes?: number;
  description?: string;
  created_at?: string;
}

export interface CaseStageChange {
  id: number;
  case_file_id: number;
  from_stage?: string | null;
  to_stage: string;
  changed_by_user_id?: number;
  changed_at?: string;
}

export interface CaseExpense {
  id: number;
  firm_id: number;
  case_file_id: number;
  expense_date?: string | null;
  description: string;
  category: string;
  amount: number;
  created_by_user_id?: number;
  created_at?: string;
}

export interface CaseFinancials {
  agreed_fee: number | null;
  total_expenses: number;
  total_invoiced: number;
  total_paid: number;
  outstanding: number;
}

export interface StageAction { key: string; label: string; available: boolean }
export interface StageGuide { focus: string; actions: StageAction[] }

export interface CaseMeta {
  stages: { key: string; label: string }[];
  event_kinds: string[];
  priorities: { key: string; label: string }[];
  doc_types: { key: string; label: string }[];
  expense_categories: { key: string; label: string }[];
  stage_guides: Record<string, StageGuide>;
  stage_flow: Record<string, string | null>;
  exhibit_statuses: { key: string; label: string }[];
  exhibit_parties: { key: string; label: string }[];
  hearing_purposes: { key: string; label: string }[];
}

// Fetch wrapper with error handling and JWT auth
export async function fetchAPI<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  try {
    // Get JWT token from Supabase session
    const { supabase } = await import('./lib/supabase');
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options?.headers as Record<string, string>),
    };

    // Add Authorization header if we have a token
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
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
export interface Lead {
  id: number;
  contact_name: string;
  phone: string | null;
  email: string | null;
  matter_summary: string | null;
  intake_notes: string | null;
  status: 'open' | 'accepted' | 'declined';
  decided_at: string | null;
  converted_case_file_id: number | null;
  created_at: string | null;
}

export interface CaseNote {
  id: number;
  case_file_id: number;
  body: string;
  pinned: boolean;
  event_id: number | null;
  document_id: number | null;
  created_by_user_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CaseExhibit {
  id: number;
  case_file_id: number;
  exhibit_mark: string | null;
  description: string | null;
  party: string | null;
  status: string;
  document_id: number | null;
  hearing_event_id: number | null;
  created_at: string | null;
}

export interface CalendarItem {
  event_id: number;
  case_file_id: number;
  case_number: string;
  case_title: string;
  court: string | null;
  client_name: string | null;
  event_date: string;
  title: string;
  purpose: string | null;
  outcome: string | null;
}

export interface Task {
  id: number;
  title: string;
  due_date: string | null;
  case_file_id: number | null;
  case_number: string | null;
  case_title: string | null;
  done: boolean;
  priority: string;
  created_at: string | null;
}

export interface Template { id: number; name: string; category: string; body: string; created_at: string | null; updated_at: string | null }
export interface Draft { id: number; title: string; body: string; case_file_id: number | null; case_number: string | null; case_title: string | null; template_id: number | null; created_at: string | null; updated_at: string | null }
export interface MergeField { token: string; label: string; source: string }
export interface WritingMeta { merge_fields: MergeField[]; template_categories: { key: string; label: string }[]; builtin_templates: { key: string; name: string; category: string; body: string }[] }

export const api = {
  // Clients
  getClients: (search?: string) => {
    const url = search ? `${API_ENDPOINTS.clients}?search=${encodeURIComponent(search)}` : API_ENDPOINTS.clients;
    return fetchAPI<Client[]>(url);
  },

  getClientsPaged: (params: { page: number; page_size?: number; search?: string }) => {
    const q = new URLSearchParams();
    q.append('page', String(params.page));
    q.append('page_size', String(params.page_size ?? 50));
    if (params.search) q.append('search', params.search);
    return fetchAPI<Paginated<Client>>(`${API_ENDPOINTS.clients}?${q}`);
  },

  getClient: (id: number) => fetchAPI<Client>(`${API_ENDPOINTS.clients}/${id}`),

  getRecentClients: (limit = 6) =>
    fetchAPI<Client[]>(`${API_ENDPOINTS.clients}/recent?limit=${limit}`),

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

  // Items (Service/Product Catalog)
  getItems: (search?: string, activeOnly: boolean = true) => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (!activeOnly) params.append('active', 'false');
    const url = params.toString() ? `${API_ENDPOINTS.items}?${params}` : API_ENDPOINTS.items;
    return fetchAPI<Item[]>(url);
  },

  getItemsPaged: (params: { page: number; page_size?: number; search?: string; activeOnly?: boolean }) => {
    const q = new URLSearchParams();
    q.append('page', String(params.page));
    q.append('page_size', String(params.page_size ?? 50));
    if (params.search) q.append('search', params.search);
    if (params.activeOnly === false) q.append('active', 'false');
    return fetchAPI<Paginated<Item>>(`${API_ENDPOINTS.items}?${q}`);
  },

  getItem: (id: number) => fetchAPI<Item>(`${API_ENDPOINTS.items}/${id}`),

  createItem: (data: Partial<Item>) =>
    fetchAPI<Item>(API_ENDPOINTS.items, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateItem: (id: number, data: Partial<Item>) =>
    fetchAPI<Item>(`${API_ENDPOINTS.items}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteItem: (id: number) =>
    fetchAPI<{ message: string }>(`${API_ENDPOINTS.items}/${id}`, {
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

  getInvoicesPaged: (params: {
    page: number;
    page_size?: number;
    status?: string;
    search?: string;
    client_id?: number;
    start_date?: string;
    end_date?: string;
    sort?: string;
    order?: 'asc' | 'desc';
  }) => {
    const q = new URLSearchParams();
    q.append('page', String(params.page));
    q.append('page_size', String(params.page_size ?? 50));
    (['status', 'search', 'client_id', 'start_date', 'end_date', 'sort', 'order'] as const).forEach((key) => {
      const value = params[key];
      if (value !== undefined && value !== null && value !== '') {
        q.append(key, String(value));
      }
    });
    return fetchAPI<Paginated<Invoice>>(`${API_ENDPOINTS.invoices}?${q}`);
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

  generatePDF: async (id: number, layout: 'single' | 'two_up' = 'single'): Promise<Blob> => {
    // Get JWT token from Supabase session
    const { supabase } = await import('./lib/supabase');
    const { data: { session } } = await supabase.auth.getSession();

    const headers: Record<string, string> = {};
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    }

    const qs = layout === 'two_up' ? '?layout=two_up' : '';
    const response = await fetch(`${API_ENDPOINTS.invoices}/${id}/generate_pdf${qs}`, {
      method: 'POST',
      headers,
    });
    if (!response.ok) {
      throw new Error('Failed to generate PDF');
    }
    return await response.blob();
  },

  duplicateInvoice: (id: number) =>
    fetchAPI<{ message: string; invoice: Invoice }>(`${API_ENDPOINTS.invoices}/${id}/duplicate`, {
      method: 'POST',
    }),

  // Send an invoice over a channel. For 'whatsapp' the result carries a
  // whatsapp_url the caller should window.open. `base_url` should be the
  // frontend origin so public links resolve in local & prod.
  sendInvoice: (
    id: number,
    payload: { channel: 'email' | 'whatsapp'; subject?: string; body?: string; base_url?: string },
  ) =>
    fetchAPI<SendResult>(`${API_ENDPOINTS.invoices}/${id}/send`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Get a signed, shareable public link to an invoice. Pass the frontend
  // origin as baseUrl so the link points at this site.
  getInvoiceShareLink: (id: number, baseUrl: string) =>
    fetchAPI<{ link: string }>(
      `${API_ENDPOINTS.invoices}/${id}/share_link?base_url=${encodeURIComponent(baseUrl)}`,
    ),

  // Public (unauthenticated) hosted-invoice fetch. No JWT needed.
  getPublicInvoice: async (userId: string, invoiceId: string, sig: string): Promise<PublicInvoice> => {
    const url = `${API_BASE_URL}/public/invoices/${userId}/${invoiceId}?sig=${encodeURIComponent(sig)}`;
    const response = await fetch(url);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }
    return response.json();
  },

  // Public PDF URL (open/download directly; no auth).
  publicPdfUrl: (userId: string, invoiceId: string, sig: string) =>
    `${API_BASE_URL}/public/invoices/${userId}/${invoiceId}/pdf?sig=${encodeURIComponent(sig)}`,

  // Recurring schedules
  getRecurring: () => fetchAPI<RecurringSchedule[]>(API_ENDPOINTS.recurring),

  createRecurring: (data: Partial<RecurringSchedule>) =>
    fetchAPI<RecurringSchedule>(API_ENDPOINTS.recurring, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateRecurring: (id: number, data: Partial<RecurringSchedule>) =>
    fetchAPI<RecurringSchedule>(`${API_ENDPOINTS.recurring}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteRecurring: (id: number) =>
    fetchAPI<{ message: string }>(`${API_ENDPOINTS.recurring}/${id}`, {
      method: 'DELETE',
    }),

  getRecurringReminders: () =>
    fetchAPI<Invoice[]>(`${API_ENDPOINTS.recurring}/reminders`),

  // Legal Feed
  getLegalFeed: (params: { page: number; page_size?: number; type?: string; court?: string }) => {
    const q = new URLSearchParams();
    q.append('page', String(params.page));
    q.append('page_size', String(params.page_size ?? 20));
    if (params.type) q.append('type', params.type);
    if (params.court) q.append('court', params.court);
    return fetchAPI<Paginated<LegalFeedItem>>(`${API_ENDPOINTS.legalFeed}?${q}`);
  },

  getLegalFeedCourts: async (): Promise<string[]> => {
    const res = await fetchAPI<{ courts: string[] }>(`${API_ENDPOINTS.legalFeed}/courts`);
    return res.courts;
  },

  getLegalFeedForYou: async (params: { type: string; limit?: number; offset?: number }): Promise<LegalFeedItem[]> => {
    const q = new URLSearchParams({
      type: params.type,
      limit: String(params.limit ?? 10),
      offset: String(params.offset ?? 0),
    });
    const res = await fetchAPI<{ data: LegalFeedItem[] }>(`${API_ENDPOINTS.legalFeed}/for-you?${q}`);
    return res.data;
  },

  postLegalFeedEvent: (item_id: number, kind: 'click' | 'not_interested') =>
    fetchAPI<{ ok: boolean }>(`${API_ENDPOINTS.legalFeed}/events`, {
      method: 'POST', body: JSON.stringify({ item_id, kind }),
    }),

  getLegalFeedPreferences: () =>
    fetchAPI<LegalFeedPreference>(`${API_ENDPOINTS.legalFeed}/preferences`),

  putLegalFeedPreferences: (p: LegalFeedPreference) =>
    fetchAPI<LegalFeedPreference>(`${API_ENDPOINTS.legalFeed}/preferences`, {
      method: 'PUT', body: JSON.stringify(p),
    }),

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

  // Authentication
  login: (email: string, password: string) =>
    fetchAPI<any>(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string) =>
    fetchAPI<any>(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  logout: () =>
    fetchAPI<any>(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
    }),

  getCurrentUser: () =>
    fetchAPI<any>(`${API_BASE_URL}/auth/me`),

  onboard: (data: any) =>
    fetchAPI<any>(`${API_BASE_URL}/auth/onboard`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateProfile: (data: {
    full_name?: string; designation?: string;
    bar_council_number?: string; personal_phone?: string;
  }) =>
    fetchAPI<any>(`${API_BASE_URL}/auth/profile`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  dismissChecklist: () =>
    fetchAPI<{ checklist_dismissed: boolean }>(`${API_BASE_URL}/auth/dismiss-checklist`, {
      method: 'POST',
    }),

  updateFirm: (data: any) =>
    fetchAPI<any>(`${API_BASE_URL}/auth/firm`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteAccount: (confirmation: string) =>
    fetchAPI<any>(`${API_BASE_URL}/auth/delete-account`, {
      method: 'DELETE',
      body: JSON.stringify({ confirmation }),
    }),

  // Storage - Image uploads
  uploadImage: async (fileType: 'logo' | 'signature', file: File) => {
    const { supabase } = await import('./lib/supabase');
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/storage/upload/${fileType}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || `Upload failed: ${response.statusText}`);
    }

    return response.json();
  },

  // ---- Firm tenancy & RBAC ----------------------------------------------
  // Firm profile
  getFirmTenant: () => fetchAPI<FirmTenant>(`${API_BASE_URL}/firm`),

  renameFirm: (name: string) =>
    fetchAPI<FirmTenant>(`${API_BASE_URL}/firm`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    }),

  // Members
  getMembers: () => fetchAPI<FirmMember[]>(`${API_BASE_URL}/firm/members`),

  changeMemberRole: (userId: number, roleId: number) =>
    fetchAPI<FirmMember>(`${API_BASE_URL}/firm/members/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify({ role_id: roleId }),
    }),

  removeMember: (userId: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/firm/members/${userId}`, {
      method: 'DELETE',
    }),

  getPermissionsCatalog: () =>
    fetchAPI<{ modules: PermissionModule[] }>(`${API_BASE_URL}/firm/permissions/catalog`),

  // Roles
  getRoles: () => fetchAPI<FirmRole[]>(`${API_BASE_URL}/firm/roles`),

  createRole: (data: { name: string; description?: string; permissions: string[] }) =>
    fetchAPI<FirmRole>(`${API_BASE_URL}/firm/roles`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateRole: (id: number, data: { name?: string; description?: string; permissions?: string[] }) =>
    fetchAPI<FirmRole>(`${API_BASE_URL}/firm/roles/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteRole: (id: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/firm/roles/${id}`, {
      method: 'DELETE',
    }),

  // Invites
  getInvites: () => fetchAPI<FirmInvite[]>(`${API_BASE_URL}/firm/invites`),

  createInvite: (data: { email: string; role_id: number }) =>
    fetchAPI<FirmInvite>(`${API_BASE_URL}/firm/invites`, {
      method: 'POST',
      body: JSON.stringify({ ...data, base_url: window.location.origin }),
    }),

  revokeInvite: (id: number) =>
    fetchAPI<FirmInvite>(`${API_BASE_URL}/firm/invites/${id}`, {
      method: 'DELETE',
    }),

  acceptInvite: (token: string) =>
    fetchAPI<{ firm_id: number; role_id: number; invite: FirmInvite }>(
      `${API_BASE_URL}/invites/accept`,
      { method: 'POST', body: JSON.stringify({ token }) },
    ),

  acceptPendingInvite: () =>
    fetchAPI<{ firm_id: number; role_id: number }>(
      `${API_BASE_URL}/invites/accept-pending`,
      { method: 'POST' },
    ),

  // ---- Case files -------------------------------------------------------
  getCaseMeta: () => fetchAPI<CaseMeta>(`${API_BASE_URL}/case-files/meta`),

  getCaseFiles: (params?: { stage?: string; client_id?: number; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.stage) q.append('stage', params.stage);
    if (params?.client_id) q.append('client_id', String(params.client_id));
    if (params?.search) q.append('search', params.search);
    const qs = q.toString();
    return fetchAPI<CaseFile[]>(`${API_BASE_URL}/case-files${qs ? `?${qs}` : ''}`);
  },

  getCaseFile: (id: number) => fetchAPI<CaseFile>(`${API_BASE_URL}/case-files/${id}`),

  createCaseFile: (data: Partial<CaseFile>) =>
    fetchAPI<CaseFile>(`${API_BASE_URL}/case-files`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseFile: (id: number, data: Partial<CaseFile>) =>
    fetchAPI<CaseFile>(`${API_BASE_URL}/case-files/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  moveCaseFile: (id: number, stage: string, position?: number) =>
    fetchAPI<CaseFile>(`${API_BASE_URL}/case-files/${id}/move`, {
      method: 'PATCH', body: JSON.stringify({ stage, position }),
    }),

  deleteCaseFile: (id: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-files/${id}`, { method: 'DELETE' }),

  getCaseEvents: (caseId: number) =>
    fetchAPI<CaseEvent[]>(`${API_BASE_URL}/case-files/${caseId}/events`),

  addCaseEvent: (caseId: number, data: { event_date: string; kind: string; title: string; notes?: string }) =>
    fetchAPI<CaseEvent>(`${API_BASE_URL}/case-files/${caseId}/events`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseEvent: (eventId: number, data: Partial<CaseEvent>) =>
    fetchAPI<CaseEvent>(`${API_BASE_URL}/case-events/${eventId}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseEvent: (eventId: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-events/${eventId}`, { method: 'DELETE' }),

  getCaseInvoices: (caseId: number) =>
    fetchAPI<Invoice[]>(`${API_BASE_URL}/invoices?case_file_id=${caseId}`),

  // ---- Leads / Enquiries ------------------------------------------------
  getLeads: (status?: string) =>
    fetchAPI<Lead[]>(`${API_BASE_URL}/leads${status ? `?status=${status}` : ''}`),

  createLead: (data: Partial<Lead>) =>
    fetchAPI<Lead>(`${API_BASE_URL}/leads`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateLead: (id: number, data: Partial<Lead>) =>
    fetchAPI<Lead>(`${API_BASE_URL}/leads/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteLead: (id: number) =>
    fetchAPI<{ ok: boolean }>(`${API_BASE_URL}/leads/${id}`, { method: 'DELETE' }),

  convertLead: (id: number, data: { title?: string; client_id?: number }) =>
    fetchAPI<CaseFile>(`${API_BASE_URL}/leads/${id}/convert`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  // ---- Case notes -------------------------------------------------------
  getCaseNotes: (caseId: number) =>
    fetchAPI<CaseNote[]>(`${API_BASE_URL}/case-files/${caseId}/notes`),

  addCaseNote: (caseId: number, data: { body: string; pinned?: boolean; event_id?: number; document_id?: number }) =>
    fetchAPI<CaseNote>(`${API_BASE_URL}/case-files/${caseId}/notes`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseNote: (id: number, data: Partial<CaseNote>) =>
    fetchAPI<CaseNote>(`${API_BASE_URL}/case-notes/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseNote: (id: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-notes/${id}`, { method: 'DELETE' }),

  // ---- Case exhibits ----------------------------------------------------
  getCaseExhibits: (caseId: number) =>
    fetchAPI<CaseExhibit[]>(`${API_BASE_URL}/case-files/${caseId}/exhibits`),

  addCaseExhibit: (caseId: number, data: Partial<CaseExhibit>) =>
    fetchAPI<CaseExhibit>(`${API_BASE_URL}/case-files/${caseId}/exhibits`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseExhibit: (id: number, data: Partial<CaseExhibit>) =>
    fetchAPI<CaseExhibit>(`${API_BASE_URL}/case-exhibits/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseExhibit: (id: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-exhibits/${id}`, { method: 'DELETE' }),

  // ---- Hearings / proceedings -------------------------------------------
  recordProceedings: (caseId: number, data: { next_date: string; purpose?: string; outcome?: string; current_event_id?: number }) =>
    fetchAPI<{ case_file: CaseFile; next_event: CaseEvent }>(`${API_BASE_URL}/case-files/${caseId}/proceedings`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  setNextDate: (caseId: number, data: { next_date: string; purpose?: string }) =>
    fetchAPI<CaseFile>(`${API_BASE_URL}/case-files/${caseId}/next-date`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  getCalendar: (from: string, to: string) =>
    fetchAPI<CalendarItem[]>(`${API_BASE_URL}/calendar?from=${from}&to=${to}`),

  // ---- Tasks ------------------------------------------------------------
  getTasks: (params?: { from?: string; to?: string; status?: string; case_file_id?: number }) => {
    const q = new URLSearchParams();
    if (params?.from) q.append('from', params.from);
    if (params?.to) q.append('to', params.to);
    if (params?.status) q.append('status', params.status);
    if (params?.case_file_id) q.append('case_file_id', String(params.case_file_id));
    const qs = q.toString();
    return fetchAPI<Task[]>(`${API_BASE_URL}/tasks${qs ? `?${qs}` : ''}`);
  },
  addTask: (data: { title: string; due_date?: string; case_file_id?: number; priority?: string }) =>
    fetchAPI<Task>(`${API_BASE_URL}/tasks`, { method: 'POST', body: JSON.stringify(data) }),
  updateTask: (id: number, data: Partial<Task>) =>
    fetchAPI<Task>(`${API_BASE_URL}/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteTask: (id: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/tasks/${id}`, { method: 'DELETE' }),

  // ---- Writing (templates + drafts) -------------------------------------
  getWritingMeta: () => fetchAPI<WritingMeta>(`${API_BASE_URL}/writing/meta`),
  getTemplates: () => fetchAPI<Template[]>(`${API_BASE_URL}/templates`),
  getTemplate: (id: number) => fetchAPI<Template>(`${API_BASE_URL}/templates/${id}`),
  createTemplate: (d: Partial<Template>) => fetchAPI<Template>(`${API_BASE_URL}/templates`, { method: 'POST', body: JSON.stringify(d) }),
  updateTemplate: (id: number, d: Partial<Template>) => fetchAPI<Template>(`${API_BASE_URL}/templates/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteTemplate: (id: number) => fetchAPI<{ message: string }>(`${API_BASE_URL}/templates/${id}`, { method: 'DELETE' }),
  getDrafts: (caseFileId?: number) => fetchAPI<Draft[]>(`${API_BASE_URL}/drafts${caseFileId ? `?case_file_id=${caseFileId}` : ''}`),
  getDraft: (id: number) => fetchAPI<Draft>(`${API_BASE_URL}/drafts/${id}`),
  createDraft: (d: Partial<Draft>) => fetchAPI<Draft>(`${API_BASE_URL}/drafts`, { method: 'POST', body: JSON.stringify(d) }),
  updateDraft: (id: number, d: Partial<Draft>) => fetchAPI<Draft>(`${API_BASE_URL}/drafts/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteDraft: (id: number) => fetchAPI<{ message: string }>(`${API_BASE_URL}/drafts/${id}`, { method: 'DELETE' }),

  // ---- Case documents ---------------------------------------------------
  getCaseDocuments: (caseId: number) =>
    fetchAPI<CaseDocument[]>(`${API_BASE_URL}/case-files/${caseId}/documents`),

  uploadCaseDocument: async (caseId: number, file: File,
                             meta: { title: string; doc_type: string; description?: string; event_id?: number }) => {
    const { supabase } = await import('./lib/supabase');
    const { data: { session } } = await supabase.auth.getSession();
    const form = new FormData();
    form.append('file', file);
    form.append('title', meta.title);
    form.append('doc_type', meta.doc_type);
    if (meta.description) form.append('description', meta.description);
    if (meta.event_id) form.append('event_id', String(meta.event_id));
    const resp = await fetch(`${API_BASE_URL}/case-files/${caseId}/documents`, {
      method: 'POST',
      headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
      body: form,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: resp.statusText }));
      throw new Error(err.error || `Upload failed: ${resp.status}`);
    }
    return resp.json() as Promise<CaseDocument>;
  },

  getDocumentDownloadUrl: (docId: number) =>
    fetchAPI<{ url: string }>(`${API_BASE_URL}/case-documents/${docId}/download`),

  updateCaseDocument: (docId: number, data: Partial<CaseDocument>) =>
    fetchAPI<CaseDocument>(`${API_BASE_URL}/case-documents/${docId}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseDocument: (docId: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-documents/${docId}`, { method: 'DELETE' }),

  // ---- Case record depth (stage history, expenses, financials) ----------
  getStageHistory: (caseId: number) =>
    fetchAPI<CaseStageChange[]>(`${API_BASE_URL}/case-files/${caseId}/stage-history`),

  getCaseFinancials: (caseId: number) =>
    fetchAPI<CaseFinancials>(`${API_BASE_URL}/case-files/${caseId}/financials`),

  getCaseExpenses: (caseId: number) =>
    fetchAPI<CaseExpense[]>(`${API_BASE_URL}/case-files/${caseId}/expenses`),

  addCaseExpense: (caseId: number, data: { expense_date?: string; description: string; category: string; amount: number }) =>
    fetchAPI<CaseExpense>(`${API_BASE_URL}/case-files/${caseId}/expenses`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseExpense: (expenseId: number, data: Partial<CaseExpense>) =>
    fetchAPI<CaseExpense>(`${API_BASE_URL}/case-expenses/${expenseId}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseExpense: (expenseId: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-expenses/${expenseId}`, { method: 'DELETE' }),

  getSignedUrl: (fileType: 'logo' | 'signature') =>
    fetchAPI<{ signed_url: string; expires_in: number; path: string }>(
      `${API_BASE_URL}/storage/signed-url/${fileType}`
    ),

  deleteImage: (fileType: 'logo' | 'signature') =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/storage/delete/${fileType}`, {
      method: 'DELETE',
    }),

  // Data export — downloads a ZIP of all the user's data + storage files
  exportData: async (): Promise<void> => {
    const { supabase } = await import('./lib/supabase');
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    const response = await fetch(`${API_BASE_URL}/backup/export`, {
      method: 'GET',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || `Export failed: ${response.statusText}`);
    }

    const blob = await response.blob();

    const disposition = response.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename=([^;]+)/i);
    const filename = match ? match[1].trim().replace(/^"|"$/g, '') : 'snappy_export.zip';

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
};
