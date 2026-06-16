import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm, useFieldArray } from 'react-hook-form';
import { api, Client, InvoiceItem, Item } from '../api';
import ItemAutocomplete from '../components/ItemAutocomplete';
import { useAuth } from '../contexts/AuthContext';
import { ArrowLeft, Plus, Trash2, RotateCcw, Search } from 'lucide-react';

interface InvoiceForm {
  client_id: number;
  invoice_date: string;
  due_date: string;
  short_desc: string;
  tax_rate: number;
  items: InvoiceItem[];
  notes?: string;
}

const formatINR = (value: number) =>
  '₹' + value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function NewInvoice() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { firm } = useAuth();
  const [clientSearch, setClientSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [originalInvoice, setOriginalInvoice] = useState<any>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(clientSearch), 300);
    return () => clearTimeout(t);
  }, [clientSearch]);

  const defaultTaxRate = firm?.default_tax_rate ?? 18;
  const showDueDate = firm?.show_due_date ?? true;

  const { register, control, handleSubmit, watch, setValue, reset } = useForm<InvoiceForm>({
    defaultValues: {
      client_id: 0,
      invoice_date: new Date().toISOString().split('T')[0],
      due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      tax_rate: defaultTaxRate,
      items: [{ description: '', quantity: 1, rate: 0, amount: 0 }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'items' });

  const { data: invoice } = useQuery({
    queryKey: ['invoice', id],
    queryFn: () => api.getInvoice(Number(id)),
    enabled: !!id,
  });

  useEffect(() => {
    if (invoice) {
      const formData = {
        client_id: invoice.client_id,
        invoice_date: invoice.invoice_date,
        due_date: invoice.due_date || '',
        short_desc: invoice.short_desc || '',
        tax_rate: invoice.tax_rate,
        items: invoice.items || [{ description: '', quantity: 1, rate: 0, amount: 0 }],
        notes: invoice.notes || '',
      };
      reset(formData);
      setOriginalInvoice(formData);
      api.getClient(invoice.client_id).then(setSelectedClient);
    }
  }, [invoice, reset]);

  const { data: clients, isLoading: clientsLoading } = useQuery({
    queryKey: ['clients', debouncedSearch],
    queryFn: () => api.getClients(debouncedSearch),
    enabled: debouncedSearch.length >= 3,
  });

  const { data: recentClients } = useQuery({
    queryKey: ['clients', 'recent'],
    queryFn: () => api.getRecentClients(6),
    enabled: !id,  // only when composing a brand-new invoice
  });

  const createMutation = useMutation({
    mutationFn: api.createInvoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      navigate('/invoices');
    },
  });
  const updateMutation = useMutation({
    mutationFn: (data: any) => api.updateInvoice(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      navigate('/invoices');
    },
  });

  const items = watch('items');
  const taxRate = watch('tax_rate');
  const subtotal = items.reduce((sum, i) => sum + (i.amount || 0), 0);
  const taxAmount = subtotal * (taxRate / 100);
  const total = subtotal + taxAmount;

  const updateItemAmount = (index: number) => {
    const item = items[index];
    setValue(`items.${index}.amount`, (item.quantity || 0) * (item.rate || 0));
  };

  const onSubmit = (data: InvoiceForm) => {
    if (id) updateMutation.mutate(data);
    else createMutation.mutate(data);
  };

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      {/* Header */}
      <div className="mb-10">
        <button
          onClick={() => navigate('/invoices')}
          className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-oxblood transition-colors mb-3"
        >
          <ArrowLeft size={14} strokeWidth={2} />
          <span>Back to invoices</span>
        </button>
        <div className="page-eyebrow">{id ? 'Amendment' : 'New entry'}</div>
        <h1 className="page-title">{id ? 'Edit invoice' : 'Compose invoice'}</h1>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Client */}
        <section className="card p-8">
          <div className="mb-5">
            <div className="page-eyebrow">Part I</div>
            <h2 className="section-title mt-1">Bill to</h2>
          </div>

          {selectedClient ? (
            <div className="bg-paper-deep border border-rule rounded-DEFAULT p-5 flex items-start justify-between gap-4">
              <div>
                <div className="font-display text-xl text-ink"
                     style={{ fontVariationSettings: '"opsz" 48, "wght" 500' }}>
                  {selectedClient.name}
                </div>
                {selectedClient.address && (
                  <div className="text-sm text-ink-soft mt-1 whitespace-pre-line">
                    {selectedClient.address}
                  </div>
                )}
                <div className="flex flex-wrap gap-4 mt-3 text-xs text-ink-muted">
                  {selectedClient.email && <span>{selectedClient.email}</span>}
                  {selectedClient.phone && <span className="font-mono">{selectedClient.phone}</span>}
                  {selectedClient.tax_id && <span className="font-mono">GSTIN: {selectedClient.tax_id}</span>}
                </div>
              </div>
              <button
                type="button"
                onClick={() => { setSelectedClient(null); setValue('client_id', 0); }}
                className="text-xs uppercase tracking-eyebrow text-ink-muted hover:text-oxblood transition-colors"
              >
                Change
              </button>
            </div>
          ) : (
            <div>
              {clientSearch.length === 0 && recentClients && recentClients.length > 0 && (
                <div className="mb-4">
                  <div className="eyebrow mb-2">Recent clients</div>
                  <div className="flex flex-wrap gap-2">
                    {recentClients.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => {
                          setSelectedClient(c);
                          setValue('client_id', c.id);
                          setValue('tax_rate', c.default_tax_rate);
                          setClientSearch('');
                        }}
                        className="px-3 py-1.5 text-sm border border-rule rounded-DEFAULT
                                   text-ink-soft hover:border-oxblood hover:text-oxblood
                                   bg-surface transition-colors"
                      >
                        {c.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <label className="field-label">Search client (min 3 characters) *</label>
              <div className="relative">
                <Search size={14} strokeWidth={1.5}
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint pointer-events-none" />
                <input
                  type="text"
                  value={clientSearch}
                  onChange={(e) => setClientSearch(e.target.value)}
                  placeholder="Start typing the client's name…"
                  className="field-input pl-9"
                  autoFocus
                />
              </div>

              {clientsLoading && clientSearch.length >= 3 && (
                <div className="mt-2 text-xs text-ink-muted">Searching catalog…</div>
              )}
              {clientSearch.length > 0 && clientSearch.length < 3 && (
                <div className="mt-2 text-xs text-ink-muted">
                  Type {3 - clientSearch.length} more character{3 - clientSearch.length > 1 ? 's' : ''}…
                </div>
              )}

              {clients && clients.length > 0 && (
                <div className="mt-3 border border-rule rounded-DEFAULT max-h-60 overflow-y-auto bg-surface">
                  {clients.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => {
                        setSelectedClient(c);
                        setValue('client_id', c.id);
                        setValue('tax_rate', c.default_tax_rate);
                        setClientSearch('');
                      }}
                      className="w-full text-left px-4 py-3 hover:bg-paper-deep border-b border-rule-soft last:border-b-0 transition-colors"
                    >
                      <div className="font-medium text-ink text-sm">{c.name}</div>
                      {c.address && <div className="text-xs text-ink-muted mt-0.5">{c.address}</div>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Details */}
        <section className="card p-8">
          <div className="mb-5">
            <div className="page-eyebrow">Part II</div>
            <h2 className="section-title mt-1">Invoice details</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="field-label">Invoice date *</label>
              <input
                type="date"
                {...register('invoice_date', { required: true })}
                className="field-input font-mono"
              />
            </div>
            {showDueDate && (
              <div>
                <label className="field-label">Due date</label>
                <input
                  type="date"
                  {...register('due_date')}
                  className="field-input font-mono"
                />
              </div>
            )}
            <div>
              <label className="field-label">Tax rate (%)</label>
              <input
                type="number"
                step="0.01"
                {...register('tax_rate', { required: true, min: 0, max: 100 })}
                className="field-input font-mono tabular"
              />
            </div>
          </div>

          <div className="mt-4">
            <label className="field-label">Short description (max 120)</label>
            <input
              type="text"
              maxLength={120}
              {...register('short_desc')}
              placeholder="Brief description of services…"
              className="field-input"
            />
            <div className="flex justify-end mt-1.5 text-2xs uppercase tracking-eyebrow text-ink-muted">
              <span className="font-mono">{watch('short_desc')?.length || 0} / 120</span>
            </div>
          </div>
        </section>

        {/* Line items */}
        <section className="card p-8">
          <div className="mb-5">
            <div className="page-eyebrow">Part III</div>
            <h2 className="section-title mt-1">Line items</h2>
          </div>

          {/* Table header */}
          <div className="grid grid-cols-[1fr_5rem_8rem_8rem_2rem] gap-4 pb-3 border-b border-rule-strong">
            <div className="eyebrow">Description</div>
            <div className="eyebrow text-center">Qty</div>
            <div className="eyebrow text-right">Rate</div>
            <div className="eyebrow text-right">Amount</div>
            <div></div>
          </div>

          <div className="divide-y divide-rule-soft">
            {fields.map((field, index) => (
              <div key={field.id} className="grid grid-cols-[1fr_5rem_8rem_8rem_2rem] gap-4 py-4 items-start">
                <div>
                  <ItemAutocomplete
                    value={items[index]?.description || ''}
                    onChange={(value) => setValue(`items.${index}.description`, value, { shouldValidate: true })}
                    onSelectItem={(item: Item) => {
                      setValue(`items.${index}.description`, item.description || item.name, { shouldValidate: true });
                      setValue(`items.${index}.rate`, item.default_rate, { shouldValidate: true });
                      const quantity = items[index]?.quantity || 1;
                      setValue(`items.${index}.amount`, quantity * item.default_rate, { shouldValidate: true });
                    }}
                    placeholder="Search or type description…"
                  />
                </div>
                <input
                  type="number"
                  step="0.01"
                  {...register(`items.${index}.quantity`, {
                    required: true, min: 0,
                    onChange: () => updateItemAmount(index),
                  })}
                  className="field-input text-center font-mono tabular"
                />
                <input
                  type="number"
                  step="0.01"
                  {...register(`items.${index}.rate`, {
                    required: true, min: 0,
                    onChange: () => updateItemAmount(index),
                  })}
                  className="field-input text-right font-mono tabular"
                />
                <div className="flex items-center justify-end h-[38px] font-mono text-sm text-ink tabular">
                  {formatINR(items[index]?.amount || 0)}
                </div>
                <button
                  type="button"
                  onClick={() => remove(index)}
                  disabled={fields.length === 1}
                  className="self-center text-ink-muted hover:text-oxblood disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  title="Remove line"
                >
                  <Trash2 size={14} strokeWidth={1.5} />
                </button>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => append({ description: '', quantity: 1, rate: 0, amount: 0 })}
            className="btn-secondary mt-5"
          >
            <Plus size={14} strokeWidth={2} />
            <span>Add line</span>
          </button>
        </section>

        {/* Totals */}
        <section className="card p-8">
          <div className="max-w-md ml-auto space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-ink-muted">Subtotal</span>
              <span className="font-mono text-ink tabular">{formatINR(subtotal)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-ink-muted">Tax ({taxRate}%)</span>
              <span className="font-mono text-ink tabular">{formatINR(taxAmount)}</span>
            </div>
            <div className="hairline" />
            <div className="flex justify-between items-baseline pt-1">
              <span className="eyebrow">Grand total</span>
              <span
                className="font-display text-3xl text-ink tabular"
                style={{ fontVariationSettings: '"opsz" 144, "wght" 500, "SOFT" 30' }}
              >
                {formatINR(total)}
              </span>
            </div>
          </div>
        </section>

        {/* Notes */}
        <section className="card p-8">
          <label className="field-label">Notes (printed on invoice)</label>
          <textarea
            {...register('notes')}
            rows={3}
            placeholder="Additional notes or payment terms…"
            className="field-textarea"
          />
        </section>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <button type="button" onClick={() => navigate('/invoices')} className="btn-ghost">
            Cancel
          </button>
          {id && originalInvoice && (
            <button type="button" onClick={() => reset(originalInvoice)} className="btn-secondary">
              <RotateCcw size={14} strokeWidth={2} />
              <span>Reset to saved</span>
            </button>
          )}
          <button
            type="submit"
            disabled={createMutation.isPending || updateMutation.isPending}
            className="btn-primary"
          >
            {createMutation.isPending || updateMutation.isPending
              ? 'Saving…'
              : (id ? 'Update invoice' : 'Create invoice')}
          </button>
        </div>
      </form>
    </div>
  );
}
