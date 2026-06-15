import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Item } from '../api';
import { Plus, Search, Pencil, Trash2, X } from 'lucide-react';

const EMPTY_FORM = {
  name: '',
  alias: '',
  description: '',
  default_rate: 0,
  unit: 'hour',
  hsn_code: '',
};

const formatRate = (rate: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
  }).format(rate);

export default function Items() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [formData, setFormData] = useState(EMPTY_FORM);

  const { data: items, isLoading } = useQuery({
    queryKey: ['items'],
    queryFn: () => api.getItems(),
  });

  const filteredItems = useMemo(() => {
    if (!items) return [];
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter((i) =>
      i.name.toLowerCase().includes(q) ||
      i.alias?.toLowerCase().includes(q) ||
      i.description?.toLowerCase().includes(q)
    );
  }, [items, searchQuery]);

  const createMutation = useMutation({
    mutationFn: api.createItem,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['items'] }); closeModal(); },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Item> }) =>
      api.updateItem(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['items'] }); closeModal(); },
  });
  const deleteMutation = useMutation({
    mutationFn: api.deleteItem,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['items'] }),
  });

  const openModal = (item?: Item) => {
    if (item) {
      setEditingItem(item);
      setFormData({
        name: item.name,
        alias: item.alias || '',
        description: item.description || '',
        default_rate: item.default_rate,
        unit: item.unit,
        hsn_code: item.hsn_code || '',
      });
    } else {
      setEditingItem(null);
      setFormData(EMPTY_FORM);
    }
    setIsModalOpen(true);
  };

  const closeModal = () => { setIsModalOpen(false); setEditingItem(null); };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingItem) updateMutation.mutate({ id: editingItem.id, data: formData });
    else createMutation.mutate(formData);
  };

  const handleDelete = (id: number) => {
    if (confirm('Deactivate this item?')) deleteMutation.mutate(id);
  };

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="flex items-end justify-between flex-wrap gap-6 mb-10">
        <div>
          <div className="page-eyebrow">Folio IV · Catalog</div>
          <h1 className="page-title">Items &amp; services</h1>
          <p className="page-subtitle">
            Your service catalog. Items added here appear in invoice line item autocomplete.
          </p>
        </div>
        <button onClick={() => openModal()} className="btn-primary">
          <Plus size={14} strokeWidth={2} />
          <span>New item</span>
        </button>
      </header>

      <div className="card p-4 mb-6 flex items-center gap-3">
        <Search size={16} strokeWidth={1.5} className="text-ink-faint shrink-0 ml-2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by name, alias, or description…"
          className="flex-1 bg-transparent border-none outline-none text-sm placeholder:text-ink-faint"
        />
        {searchQuery && (
          <span className="text-xs text-ink-muted tabular shrink-0 mr-2">
            {filteredItems.length} match{filteredItems.length === 1 ? '' : 'es'}
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="card p-16 flex justify-center"><div className="spinner" /></div>
      ) : filteredItems && filteredItems.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-rule border border-rule">
          {filteredItems.map((item) => (
            <article key={item.id} className="bg-surface p-6 hover:bg-paper-deep/50 transition-colors group">
              <header className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0 flex-1">
                  <h3 className="font-display text-lg text-ink leading-snug truncate"
                      style={{ fontVariationSettings: '"opsz" 48, "wght" 500' }}>
                    {item.name}
                  </h3>
                  {item.alias && (
                    <span className="inline-block mt-1 text-2xs font-mono text-oxblood bg-oxblood-wash px-1.5 py-0.5 rounded-sm">
                      @{item.alias}
                    </span>
                  )}
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <button
                    onClick={() => openModal(item)}
                    className="p-1.5 text-ink-muted hover:text-ink hover:bg-paper-deep rounded-sm transition-colors"
                    title="Edit"
                  >
                    <Pencil size={13} strokeWidth={1.75} />
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="p-1.5 text-ink-muted hover:text-oxblood hover:bg-oxblood-wash rounded-sm transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={13} strokeWidth={1.75} />
                  </button>
                </div>
              </header>

              {item.description && (
                <p className="text-sm text-ink-muted line-clamp-2 mb-4">{item.description}</p>
              )}

              <div className="hairline pt-4 mt-auto flex items-baseline justify-between">
                <div>
                  <div className="font-display text-2xl text-ink tabular"
                       style={{ fontVariationSettings: '"opsz" 48, "wght" 500' }}>
                    {formatRate(item.default_rate)}
                  </div>
                  <div className="text-2xs uppercase tracking-eyebrow text-ink-muted">per {item.unit}</div>
                </div>
                {item.hsn_code && (
                  <div className="text-right">
                    <div className="eyebrow">HSN</div>
                    <div className="font-mono text-xs text-ink mt-1">{item.hsn_code}</div>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="card p-16 text-center">
          <div className="page-eyebrow">Empty catalog</div>
          <h2 className="section-title mt-2">No items yet</h2>
          <p className="text-base text-ink-muted mt-3">
            Create items for services you bill often — they'll autocomplete on invoices.
          </p>
          <button onClick={() => openModal()} className="btn-primary mt-6">
            <Plus size={14} strokeWidth={2} />
            <span>Add first item</span>
          </button>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={closeModal} />

          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-2xl w-full
                          max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />

            <div className="p-8">
              <button
                onClick={closeModal}
                className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted transition-colors"
                aria-label="Close"
              >
                <X size={20} strokeWidth={1.5} />
              </button>

              <div className="mb-6">
                <div className="page-eyebrow">{editingItem ? 'Edit entry' : 'New entry'}</div>
                <h2 className="page-title !text-2xl">
                  {editingItem ? editingItem.name : 'New item'}
                </h2>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="field-label">Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="field-input"
                    placeholder="e.g., Legal Consultation"
                    autoFocus
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Alias (quick search)</label>
                    <input
                      type="text"
                      value={formData.alias}
                      onChange={(e) => setFormData({ ...formData, alias: e.target.value })}
                      className="field-input font-mono"
                      placeholder="consult, lc"
                    />
                  </div>
                  <div>
                    <label className="field-label">HSN/SAC code</label>
                    <input
                      type="text"
                      value={formData.hsn_code}
                      onChange={(e) => setFormData({ ...formData, hsn_code: e.target.value })}
                      className="field-input font-mono"
                      placeholder="998231"
                    />
                  </div>
                </div>

                <div>
                  <label className="field-label">Description (printed on invoice)</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className="field-textarea"
                    placeholder="Description that appears on each invoice line"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Default rate (₹)</label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.default_rate}
                      onChange={(e) => setFormData({
                        ...formData,
                        default_rate: parseFloat(e.target.value) || 0,
                      })}
                      className="field-input font-mono tabular"
                    />
                  </div>
                  <div>
                    <label className="field-label">Unit</label>
                    <select
                      value={formData.unit}
                      onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                      className="field-select"
                    >
                      <option value="hour">Hour</option>
                      <option value="day">Day</option>
                      <option value="unit">Unit</option>
                      <option value="fixed">Fixed</option>
                      <option value="meeting">Meeting</option>
                      <option value="hearing">Hearing</option>
                    </select>
                  </div>
                </div>

                <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                  <button type="button" onClick={closeModal} className="btn-ghost">Cancel</button>
                  <button type="submit" className="btn-primary">
                    {editingItem ? 'Save changes' : 'Create item'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
