import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm, useFieldArray } from 'react-hook-form';
import { api, Client, InvoiceItem, Item } from '../api';
import ItemAutocomplete from '../components/ItemAutocomplete';
import { useAuth } from '../contexts/AuthContext';

interface InvoiceForm {
  client_id: number;
  invoice_date: string;
  due_date: string;
  short_desc: string;
  tax_rate: number;
  items: InvoiceItem[];
  notes?: string;
}

export default function NewInvoice() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { firm } = useAuth();
  const [clientSearch, setClientSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [originalInvoice, setOriginalInvoice] = useState<any>(null);

  // Debounce client search - wait 300ms after typing stops
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(clientSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [clientSearch]);

  // Get default tax rate from firm settings
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

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'items',
  });

  // Load invoice if editing
  const { data: invoice } = useQuery({
    queryKey: ['invoice', id],
    queryFn: () => api.getInvoice(Number(id)),
    enabled: !!id,
  });

  // Populate form when editing
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

      // Load client info
      api.getClient(invoice.client_id).then((client) => {
        setSelectedClient(client);
      });
    }
  }, [invoice, reset]);

  // Client search - uses debounced value with 3-char minimum
  const { data: clients, isLoading: clientsLoading } = useQuery({
    queryKey: ['clients', debouncedSearch],
    queryFn: () => api.getClients(debouncedSearch),
    enabled: debouncedSearch.length >= 3,
  });

  // Create/Update mutations
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

  // Watch items for auto-calculation
  const items = watch('items');
  const taxRate = watch('tax_rate');

  // Calculate totals
  const subtotal = items.reduce((sum, item) => sum + (item.amount || 0), 0);
  const taxAmount = subtotal * (taxRate / 100);
  const total = subtotal + taxAmount;

  // Update item amount when quantity or rate changes
  const updateItemAmount = (index: number) => {
    const item = items[index];
    const amount = (item.quantity || 0) * (item.rate || 0);
    setValue(`items.${index}.amount`, amount);
  };

  const onSubmit = (data: InvoiceForm) => {
    if (id) {
      updateMutation.mutate(data);
    } else {
      createMutation.mutate(data);
    }
  };

  const formatCurrency = (value: number) => `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{id ? 'Edit Invoice' : 'New Invoice'}</h1>
        <p className="text-gray-600 mt-1">Create or update invoice details</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Client Selection */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Client Information</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Client *
            </label>
            <input
              type="text"
              value={clientSearch}
              onChange={(e) => setClientSearch(e.target.value)}
              placeholder="Type at least 3 characters..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />

            {/* Loading indicator */}
            {clientsLoading && clientSearch.length >= 3 && (
              <div className="mt-2 text-sm text-gray-500">Searching...</div>
            )}

            {/* Hint for minimum characters */}
            {clientSearch.length > 0 && clientSearch.length < 3 && (
              <div className="mt-2 text-sm text-gray-500">Type {3 - clientSearch.length} more character{3 - clientSearch.length > 1 ? 's' : ''}...</div>
            )}

            {clients && clients.length > 0 && (
              <div className="mt-2 border border-gray-200 rounded-lg max-h-60 overflow-y-auto">
                {clients.map((client) => (
                  <button
                    key={client.id}
                    type="button"
                    onClick={() => {
                      setSelectedClient(client);
                      setValue('client_id', client.id);
                      setValue('tax_rate', client.default_tax_rate);
                      setClientSearch('');
                    }}
                    className="w-full text-left px-4 py-3 hover:bg-primary-50 border-b last:border-b-0"
                  >
                    <div className="font-medium">{client.name}</div>
                    {client.address && <div className="text-sm text-gray-600">{client.address}</div>}
                    {client.email && <div className="text-xs text-gray-500">{client.email}</div>}
                  </button>
                ))}
              </div>
            )}

            {selectedClient && (
              <div className="mt-4 p-4 bg-primary-50 rounded-lg">
                <div className="font-medium text-primary-900">{selectedClient.name}</div>
                {selectedClient.address && <div className="text-sm text-primary-700">{selectedClient.address}</div>}
                {selectedClient.email && <div className="text-sm text-primary-700">{selectedClient.email}</div>}
                {selectedClient.phone && <div className="text-sm text-primary-700">{selectedClient.phone}</div>}
              </div>
            )}
          </div>
        </div>

        {/* Invoice Details */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Invoice Details</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Invoice Date *
              </label>
              <input
                type="date"
                {...register('invoice_date', { required: true })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {showDueDate && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Due Date
                </label>
                <input
                  type="date"
                  {...register('due_date')}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tax Rate (%)
              </label>
              <input
                type="number"
                step="0.01"
                {...register('tax_rate', { required: true, min: 0, max: 100 })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Short Description (max 120 chars)
            </label>
            <input
              type="text"
              maxLength={120}
              {...register('short_desc')}
              placeholder="Brief description of services..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
            <div className="text-xs text-gray-500 mt-1">
              {watch('short_desc')?.length || 0}/120 characters
            </div>
          </div>
        </div>

        {/* Line Items */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Line Items</h2>

          {/* Table Header */}
          <div className="flex gap-4 items-center border-b pb-3 mb-4 bg-gray-50 -mx-6 px-6 py-2">
            <div className="flex-1 text-sm font-medium text-gray-700">Description</div>
            <div className="w-24 text-sm font-medium text-gray-700 text-center">Qty</div>
            <div className="w-32 text-sm font-medium text-gray-700 text-center">Rate</div>
            <div className="w-32 text-sm font-medium text-gray-700 text-right">Amount</div>
            <div className="w-8"></div>
          </div>

          <div className="space-y-4">
            {fields.map((field, index) => (
              <div key={field.id} className="flex gap-4 items-start border-b pb-4">
                <div className="flex-1">
                  <ItemAutocomplete
                    value={items[index]?.description || ''}
                    onChange={(value) => setValue(`items.${index}.description`, value, { shouldValidate: true })}
                    onSelectItem={(item: Item) => {
                      setValue(`items.${index}.description`, item.description || item.name, { shouldValidate: true });
                      setValue(`items.${index}.rate`, item.default_rate, { shouldValidate: true });
                      // Calculate amount directly using the new rate
                      const quantity = items[index]?.quantity || 1;
                      const amount = quantity * item.default_rate;
                      setValue(`items.${index}.amount`, amount, { shouldValidate: true });
                    }}
                    placeholder="Search item or type description..."
                  />
                </div>
                <div className="w-24">
                  <input
                    type="number"
                    step="0.01"
                    {...register(`items.${index}.quantity`, {
                      required: true,
                      min: 0,
                      onChange: () => updateItemAmount(index)
                    })}
                    placeholder="Qty"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-center"
                  />
                </div>
                <div className="w-32">
                  <input
                    type="number"
                    step="0.01"
                    {...register(`items.${index}.rate`, {
                      required: true,
                      min: 0,
                      onChange: () => updateItemAmount(index)
                    })}
                    placeholder="Rate"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-right"
                  />
                </div>
                <div className="w-32 flex items-center justify-end">
                  <span className="font-medium">{formatCurrency(items[index]?.amount || 0)}</span>
                </div>
                <button
                  type="button"
                  onClick={() => remove(index)}
                  disabled={fields.length === 1}
                  className="text-red-600 hover:text-red-800 disabled:opacity-50 w-8"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => append({ description: '', quantity: 1, rate: 0, amount: 0 })}
            className="mt-4 px-4 py-2 text-primary-600 border border-primary-600 rounded-lg hover:bg-primary-50"
          >
            + Add Item
          </button>
        </div>

        {/* Totals */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="max-w-md ml-auto space-y-2">
            <div className="flex justify-between text-lg">
              <span>Subtotal:</span>
              <span className="font-medium">{formatCurrency(subtotal)}</span>
            </div>
            <div className="flex justify-between text-lg">
              <span>Tax ({taxRate}%):</span>
              <span className="font-medium">{formatCurrency(taxAmount)}</span>
            </div>
            <div className="flex justify-between text-2xl font-bold border-t pt-2">
              <span>Total:</span>
              <span className="text-primary-600">{formatCurrency(total)}</span>
            </div>
          </div>
        </div>

        {/* Notes */}
        <div className="bg-white rounded-lg shadow p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Notes
          </label>
          <textarea
            {...register('notes')}
            rows={3}
            placeholder="Additional notes or payment terms..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-4 justify-end">
          <button
            type="button"
            onClick={() => navigate('/invoices')}
            className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          {id && originalInvoice && (
            <button
              type="button"
              onClick={() => reset(originalInvoice)}
              className="px-6 py-3 border border-primary-600 text-primary-600 rounded-lg hover:bg-primary-50"
            >
              Reset to Saved
            </button>
          )}
          <button
            type="submit"
            disabled={createMutation.isPending || updateMutation.isPending}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {id ? 'Update Invoice' : 'Create Invoice'}
          </button>
        </div>
      </form>
    </div>
  );
}
