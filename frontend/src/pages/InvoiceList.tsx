import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useState } from 'react';
import { api } from '../api';

export default function InvoiceList() {
  const [filters, setFilters] = useState({
    status: '',
    search: '',
  });
  const [statusMenuOpen, setStatusMenuOpen] = useState<number | null>(null);

  const queryClient = useQueryClient();

  const { data: invoices, isLoading } = useQuery({
    queryKey: ['invoices', filters],
    queryFn: () => api.getInvoices(filters),
  });

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

  const handleStatusChange = (id: number, status: string) => {
    if (status === 'paid') {
      markPaidMutation.mutate(id);
    } else {
      updateStatusMutation.mutate({ id, status });
    }
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
            <input
              type="text"
              data-search
              placeholder="Invoice number or description..."
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
        </div>
      </div>

      {/* Invoice Table */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="spinner mx-auto"></div>
          </div>
        ) : invoices && invoices.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Invoice No.
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Client
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
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
                {invoices.map((invoice) => (
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
                    <Link
                      to={`/invoices/${invoice.id}/edit`}
                      className="text-primary-600 hover:text-primary-800"
                    >
                      Edit
                    </Link>
                    <button
                      onClick={() => handleGeneratePDF(invoice.id, invoice.invoice_number)}
                      className="text-primary-600 hover:text-primary-800"
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
    </div>
  );
}
