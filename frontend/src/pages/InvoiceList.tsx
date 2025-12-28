import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useState, useMemo } from 'react';
import { api, Invoice, Client } from '../api';
import InvoicePreview from '../components/InvoicePreview';

type SortField = 'invoice_date' | 'client_name' | 'invoice_number' | 'total';
type SortOrder = 'asc' | 'desc';

export default function InvoiceList() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState({
    status: '',
    search: '',
    client_id: '',
    start_date: '',
    end_date: '',
  });
  const [sortField, setSortField] = useState<SortField>('invoice_date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [statusMenuOpen, setStatusMenuOpen] = useState<number | null>(null);
  const [previewInvoice, setPreviewInvoice] = useState<Invoice | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  const queryClient = useQueryClient();

  // Fetch invoices with filters
  const { data: invoices, isLoading } = useQuery({
    queryKey: ['invoices', filters],
    queryFn: () => api.getInvoices({
      status: filters.status || undefined,
      search: filters.search || undefined,
      client_id: filters.client_id ? Number(filters.client_id) : undefined,
      start_date: filters.start_date || undefined,
      end_date: filters.end_date || undefined,
    }),
  });

  // Fetch clients for filter dropdown
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
  });

  // Sort invoices
  const sortedInvoices = useMemo(() => {
    if (!invoices) return [];
    return [...invoices].sort((a, b) => {
      let aVal: any, bVal: any;
      switch (sortField) {
        case 'invoice_date':
          aVal = new Date(a.invoice_date).getTime();
          bVal = new Date(b.invoice_date).getTime();
          break;
        case 'client_name':
          aVal = (a.client_name || '').toLowerCase();
          bVal = (b.client_name || '').toLowerCase();
          break;
        case 'invoice_number':
          aVal = a.invoice_number;
          bVal = b.invoice_number;
          break;
        case 'total':
          aVal = a.total;
          bVal = b.total;
          break;
        default:
          return 0;
      }
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [invoices, sortField, sortOrder]);

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.updateInvoice(id, { status: status as 'draft' | 'sent' | 'paid' | 'void' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      setStatusMenuOpen(null);
    },
  });

  const markPaidMutation = useMutation({
    mutationFn: (id: number) => api.markInvoicePaid(id, new Date().toISOString().split('T')[0]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      setStatusMenuOpen(null);
    },
  });

  const duplicateMutation = useMutation({
    mutationFn: (id: number) => api.duplicateInvoice(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      // Navigate to edit the new invoice
      navigate(`/invoices/${data.invoice.id}/edit`);
    },
  });

  const handleStatusChange = (id: number, status: string) => {
    if (status === 'paid') {
      markPaidMutation.mutate(id);
    } else {
      updateStatusMutation.mutate({ id, status });
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return '↕';
    return sortOrder === 'asc' ? '↑' : '↓';
  };

  const formatCurrency = (value: number) => `₹${value.toLocaleString('en-IN')}`;
  const formatDate = (date: string) => new Date(date).toLocaleDateString('en-IN');

  const handleGeneratePDF = async (id: number, invoiceNumber: string) => {
    try {
      const blob = await api.generatePDF(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `SNAPPY_INV_${invoiceNumber.replace(/\//g, '_')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to generate PDF:', error);
      alert('Failed to generate PDF');
    }
  };

  const handleDuplicate = (id: number) => {
    if (confirm('Create a duplicate of this invoice?')) {
      duplicateMutation.mutate(id);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      draft: 'bg-gray-100 text-gray-800',
      sent: 'bg-blue-100 text-blue-800',
      paid: 'bg-green-100 text-green-800',
      void: 'bg-red-100 text-red-800',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status as keyof typeof styles] || styles.draft}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  const clearFilters = () => {
    setFilters({
      status: '',
      search: '',
      client_id: '',
      start_date: '',
      end_date: '',
    });
  };

  return (
    <div className="p-8">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Invoices</h1>
          <p className="text-gray-600 mt-1">Manage and track all invoices</p>
        </div>
        <Link
          to="/invoices/new"
          className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
        >
          + New Invoice
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
            <input
              type="text"
              data-search
              placeholder="Invoice # or description..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="paid">Paid</option>
              <option value="void">Void</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Client</label>
            <select
              value={filters.client_id}
              onChange={(e) => setFilters({ ...filters, client_id: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Clients</option>
              {clients?.map((client: Client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">From Date</label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">To Date</label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>
        {(filters.status || filters.search || filters.client_id || filters.start_date || filters.end_date) && (
          <button
            onClick={clearFilters}
            className="mt-4 text-sm text-primary-600 hover:text-primary-800"
          >
            Clear all filters
          </button>
        )}
      </div>

      {/* Invoice Table */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="spinner mx-auto"></div>
          </div>
        ) : sortedInvoices && sortedInvoices.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('invoice_number')}
                  >
                    Invoice No. {getSortIcon('invoice_number')}
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('invoice_date')}
                  >
                    Date {getSortIcon('invoice_date')}
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('client_name')}
                  >
                    Client {getSortIcon('client_name')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('total')}
                  >
                    Amount {getSortIcon('total')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sortedInvoices.map((invoice) => (
                  <tr key={invoice.id} className="hover:bg-gray-50 relative">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {invoice.invoice_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(invoice.invoice_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {invoice.client_name}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {invoice.short_desc || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {formatCurrency(invoice.total)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="relative inline-block">
                        <button
                          onClick={() => setStatusMenuOpen(statusMenuOpen === invoice.id ? null : invoice.id)}
                          className="flex items-center space-x-1"
                        >
                          {getStatusBadge(invoice.status)}
                          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                        {statusMenuOpen === invoice.id && (
                          <>
                            <div
                              className="fixed inset-0 z-10"
                              onClick={() => setStatusMenuOpen(null)}
                            />
                            <div className="absolute left-0 z-20 mt-2 w-36 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5">
                              <div className="py-1" role="menu">
                                {['draft', 'sent', 'paid', 'void'].map((status) => (
                                  <button
                                    key={status}
                                    onClick={() => handleStatusChange(invoice.id, status)}
                                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                                    disabled={invoice.status === status}
                                  >
                                    {status.charAt(0).toUpperCase() + status.slice(1)}
                                    {invoice.status === status && ' ✓'}
                                  </button>
                                ))}
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 space-x-2">
                      <button
                        onClick={() => {
                          setPreviewInvoice(invoice);
                          setIsPreviewOpen(true);
                        }}
                        className="text-indigo-600 hover:text-indigo-800"
                      >
                        Preview
                      </button>
                      <Link
                        to={`/invoices/${invoice.id}/edit`}
                        className="text-primary-600 hover:text-primary-800"
                      >
                        Edit
                      </Link>
                      <button
                        onClick={() => handleDuplicate(invoice.id)}
                        className="text-amber-600 hover:text-amber-800"
                        disabled={duplicateMutation.isPending}
                      >
                        Duplicate
                      </button>
                      <button
                        onClick={() => handleGeneratePDF(invoice.id, invoice.invoice_number)}
                        className="text-green-600 hover:text-green-800"
                      >
                        PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-gray-500">
            <p className="text-lg mb-4">No invoices found</p>
            <Link
              to="/invoices/new"
              className="text-primary-600 hover:text-primary-800 font-medium"
            >
              Create your first invoice
            </Link>
          </div>
        )}
      </div>

      {/* Invoice Preview Modal */}
      <InvoicePreview
        invoice={previewInvoice}
        isOpen={isPreviewOpen}
        onClose={() => {
          setIsPreviewOpen(false);
          setPreviewInvoice(null);
        }}
      />
    </div>
  );
}
