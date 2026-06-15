import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useState, useMemo } from 'react';
import { api, Invoice, Client } from '../api';
import InvoicePreview from '../components/InvoicePreview';
import {
  Plus, Search, ChevronDown, ChevronUp, ChevronsUpDown,
  Eye, Pencil, Copy, Download, X,
} from 'lucide-react';

type SortField = 'invoice_date' | 'client_name' | 'invoice_number' | 'total';
type SortOrder = 'asc' | 'desc';

const formatINR = (value: number) =>
  '₹' + value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const formatDate = (date: string) =>
  new Date(date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

const statusPill: Record<string, string> = {
  draft:   'pill-draft',
  sent:    'pill-pending',
  paid:    'pill-paid',
  void:    'pill-overdue',
};

export default function InvoiceList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    status: '', search: '', client_id: '', start_date: '', end_date: '',
  });
  const [sortField, setSortField] = useState<SortField>('invoice_date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [statusMenuOpen, setStatusMenuOpen] = useState<number | null>(null);
  const [previewInvoice, setPreviewInvoice] = useState<Invoice | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

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

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
  });

  const sortedInvoices = useMemo(() => {
    if (!invoices) return [];
    return [...invoices].sort((a, b) => {
      let aV: any, bV: any;
      switch (sortField) {
        case 'invoice_date':   aV = new Date(a.invoice_date).getTime(); bV = new Date(b.invoice_date).getTime(); break;
        case 'client_name':    aV = (a.client_name || '').toLowerCase(); bV = (b.client_name || '').toLowerCase(); break;
        case 'invoice_number': aV = a.invoice_number; bV = b.invoice_number; break;
        case 'total':          aV = a.total; bV = b.total; break;
        default: return 0;
      }
      if (aV < bV) return sortOrder === 'asc' ? -1 : 1;
      if (aV > bV) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [invoices, sortField, sortOrder]);

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.updateInvoice(id, { status: status as 'draft' | 'sent' | 'paid' | 'void' }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['invoices'] }); setStatusMenuOpen(null); },
  });
  const markPaidMutation = useMutation({
    mutationFn: (id: number) => api.markInvoicePaid(id, new Date().toISOString().split('T')[0]),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['invoices'] }); setStatusMenuOpen(null); },
  });
  const duplicateMutation = useMutation({
    mutationFn: (id: number) => api.duplicateInvoice(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      navigate(`/invoices/${data.invoice.id}/edit`);
    },
  });

  const handleStatusChange = (id: number, status: string) => {
    if (status === 'paid') markPaidMutation.mutate(id);
    else updateStatusMutation.mutate({ id, status });
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortOrder('desc'); }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ChevronsUpDown size={11} strokeWidth={2} className="text-ink-faint" />;
    return sortOrder === 'asc'
      ? <ChevronUp size={11} strokeWidth={2} className="text-oxblood" />
      : <ChevronDown size={11} strokeWidth={2} className="text-oxblood" />;
  };

  const handleGeneratePDF = async (id: number, invoiceNumber: string) => {
    try {
      const blob = await api.generatePDF(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `SNAPPY_INV_${invoiceNumber.replace(/\//g, '_')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      alert('Failed to generate PDF');
    }
  };

  const handleDuplicate = (id: number) => {
    if (confirm('Create a duplicate of this invoice?')) duplicateMutation.mutate(id);
  };

  const clearFilters = () => setFilters({ status: '', search: '', client_id: '', start_date: '', end_date: '' });
  const hasFilters = !!(filters.status || filters.search || filters.client_id || filters.start_date || filters.end_date);

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      {/* Header */}
      <header className="flex items-end justify-between flex-wrap gap-6 mb-10">
        <div>
          <div className="page-eyebrow">Folio II · Invoices</div>
          <h1 className="page-title">Invoice register</h1>
          <p className="page-subtitle">
            Every invoice issued, in order. Filter, sort, mark paid, regenerate PDFs.
          </p>
        </div>
        <Link to="/invoices/new" className="btn-primary">
          <Plus size={14} strokeWidth={2} />
          <span>New invoice</span>
        </Link>
      </header>

      {/* Filters */}
      <div className="card p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="lg:col-span-2">
            <label className="field-label">Search</label>
            <div className="relative">
              <Search size={14} strokeWidth={1.5}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint pointer-events-none" />
              <input
                type="text"
                data-search
                placeholder="Invoice # or description"
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="field-input pl-9"
              />
            </div>
          </div>
          <div>
            <label className="field-label">Status</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="field-select"
            >
              <option value="">All</option>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="paid">Paid</option>
              <option value="void">Void</option>
            </select>
          </div>
          <div>
            <label className="field-label">Client</label>
            <select
              value={filters.client_id}
              onChange={(e) => setFilters({ ...filters, client_id: e.target.value })}
              className="field-select"
            >
              <option value="">All clients</option>
              {clients?.map((c: Client) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2 lg:col-span-1">
            <div>
              <label className="field-label">From</label>
              <input
                type="date"
                value={filters.start_date}
                onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
                className="field-input font-mono text-xs px-2"
              />
            </div>
            <div>
              <label className="field-label">To</label>
              <input
                type="date"
                value={filters.end_date}
                onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
                className="field-input font-mono text-xs px-2"
              />
            </div>
          </div>
        </div>

        {hasFilters && (
          <div className="mt-4 pt-4 border-t border-rule-soft flex items-center justify-between">
            <span className="eyebrow">Filters active</span>
            <button onClick={clearFilters}
                    className="text-xs uppercase tracking-eyebrow text-oxblood hover:text-oxblood-deep flex items-center gap-1">
              <X size={11} strokeWidth={2} />
              <span>Clear all</span>
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-16 flex justify-center"><div className="spinner" /></div>
        ) : sortedInvoices && sortedInvoices.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="table-editorial">
              <thead>
                <tr>
                  <th className="cursor-pointer hover:text-ink" onClick={() => handleSort('invoice_number')}>
                    <span className="inline-flex items-center gap-1.5">Invoice no. <SortIcon field="invoice_number" /></span>
                  </th>
                  <th className="cursor-pointer hover:text-ink" onClick={() => handleSort('invoice_date')}>
                    <span className="inline-flex items-center gap-1.5">Date <SortIcon field="invoice_date" /></span>
                  </th>
                  <th className="cursor-pointer hover:text-ink" onClick={() => handleSort('client_name')}>
                    <span className="inline-flex items-center gap-1.5">Client <SortIcon field="client_name" /></span>
                  </th>
                  <th>Description</th>
                  <th className="cursor-pointer hover:text-ink !text-right" onClick={() => handleSort('total')}>
                    <span className="inline-flex items-center gap-1.5">Amount <SortIcon field="total" /></span>
                  </th>
                  <th>Status</th>
                  <th className="!text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedInvoices.map((invoice) => (
                  <tr key={invoice.id}>
                    <td className="font-mono text-ink">{invoice.invoice_number}</td>
                    <td className="font-mono text-ink-muted tabular">{formatDate(invoice.invoice_date)}</td>
                    <td className="text-ink">{invoice.client_name}</td>
                    <td className="text-ink-muted max-w-xs truncate">{invoice.short_desc || '—'}</td>
                    <td className="text-right font-mono text-ink tabular">{formatINR(invoice.total)}</td>
                    <td>
                      <div className="relative inline-block">
                        <button
                          onClick={() => setStatusMenuOpen(statusMenuOpen === invoice.id ? null : invoice.id)}
                          className="flex items-center gap-1 hover:opacity-80 transition-opacity"
                        >
                          <span className={statusPill[invoice.status] || 'pill-draft'}>
                            {invoice.status}
                          </span>
                          <ChevronDown size={11} strokeWidth={2} className="text-ink-faint" />
                        </button>
                        {statusMenuOpen === invoice.id && (
                          <>
                            <div className="fixed inset-0 z-10" onClick={() => setStatusMenuOpen(null)} />
                            <div className="absolute left-0 z-20 mt-1.5 min-w-[140px] bg-surface
                                            border border-rule rounded-DEFAULT shadow-modal py-1">
                              {(['draft', 'sent', 'paid', 'void'] as const).map((s) => (
                                <button
                                  key={s}
                                  onClick={() => handleStatusChange(invoice.id, s)}
                                  disabled={invoice.status === s}
                                  className="w-full text-left px-3 py-1.5 text-sm text-ink-soft
                                             hover:bg-paper-deep disabled:opacity-40 flex items-center justify-between"
                                >
                                  <span className="capitalize">{s}</span>
                                  {invoice.status === s && <span className="text-oxblood">✓</span>}
                                </button>
                              ))}
                            </div>
                          </>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center justify-end gap-0.5">
                        <button
                          onClick={async () => {
                            const full = await api.getInvoice(invoice.id);
                            setPreviewInvoice(full);
                            setIsPreviewOpen(true);
                          }}
                          className="p-1.5 text-ink-muted hover:text-ink hover:bg-paper-deep rounded-sm transition-colors"
                          title="Preview"
                        >
                          <Eye size={14} strokeWidth={1.5} />
                        </button>
                        <Link
                          to={`/invoices/${invoice.id}/edit`}
                          className="p-1.5 text-ink-muted hover:text-ink hover:bg-paper-deep rounded-sm transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} strokeWidth={1.5} />
                        </Link>
                        <button
                          onClick={() => handleDuplicate(invoice.id)}
                          disabled={duplicateMutation.isPending}
                          className="p-1.5 text-ink-muted hover:text-ink hover:bg-paper-deep rounded-sm transition-colors disabled:opacity-40"
                          title="Duplicate"
                        >
                          <Copy size={14} strokeWidth={1.5} />
                        </button>
                        <button
                          onClick={() => handleGeneratePDF(invoice.id, invoice.invoice_number)}
                          className="p-1.5 text-ink-muted hover:text-oxblood hover:bg-oxblood-wash rounded-sm transition-colors"
                          title="Download PDF"
                        >
                          <Download size={14} strokeWidth={1.5} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-16 text-center">
            <div className="page-eyebrow">Empty register</div>
            <h2 className="section-title mt-2">
              {hasFilters ? 'No invoices match your filters' : 'No invoices yet'}
            </h2>
            <p className="text-base text-ink-muted mt-3">
              {hasFilters
                ? 'Try widening your search or clearing filters.'
                : 'Create your first invoice to get started.'}
            </p>
            {!hasFilters && (
              <Link to="/invoices/new" className="btn-primary mt-6 inline-flex">
                <Plus size={14} strokeWidth={2} />
                <span>Create first invoice</span>
              </Link>
            )}
          </div>
        )}
      </div>

      <InvoicePreview
        invoice={previewInvoice}
        isOpen={isPreviewOpen}
        onClose={() => { setIsPreviewOpen(false); setPreviewInvoice(null); }}
      />
    </div>
  );
}
