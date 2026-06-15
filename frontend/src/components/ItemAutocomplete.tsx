import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Item } from '../api';
import { Plus, X } from 'lucide-react';

interface ItemAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelectItem: (item: Item) => void;
  placeholder?: string;
  className?: string;
}

const formatRate = (rate: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
  }).format(rate);

export default function ItemAutocomplete({
  value,
  onChange,
  onSelectItem,
  placeholder = 'Search items or type description…',
  className = '',
}: ItemAutocompleteProps) {
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newItemForm, setNewItemForm] = useState({
    name: '',
    alias: '',
    description: '',
    default_rate: 0,
    unit: 'hour',
    hsn_code: '',
  });

  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: items } = useQuery({
    queryKey: ['items-search', search],
    queryFn: () => api.getItems(search, true),
    enabled: search.length >= 2,
    staleTime: 5000,
  });

  const createMutation = useMutation({
    mutationFn: api.createItem,
    onSuccess: (newItem) => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      queryClient.invalidateQueries({ queryKey: ['items-search'] });
      setShowAddModal(false);
      onChange(newItem.description || newItem.name);
      onSelectItem(newItem);
      resetForm();
    },
    onError: (error) => alert(`Failed to create item: ${error.message}`),
  });

  const resetForm = () => setNewItemForm({
    name: '', alias: '', description: '',
    default_rate: 0, unit: 'hour', hsn_code: '',
  });

  useEffect(() => {
    const onMouseDown = (e: MouseEvent) => {
      if (
        dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current && !inputRef.current.contains(e.target as Node)
      ) setIsOpen(false);
    };
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    onChange(v);
    setSearch(v);
    setIsOpen(v.length >= 2);
  };

  const handleSelectItem = (item: Item) => {
    onChange(item.description || item.name);
    onSelectItem(item);
    setIsOpen(false);
    setSearch('');
  };

  const handleAddNewItem = () => {
    setNewItemForm({ ...newItemForm, name: search, description: search });
    setShowAddModal(true);
    setIsOpen(false);
  };

  const handleCreateItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemForm.name.trim()) return;
    createMutation.mutate(newItemForm);
  };

  const hasNoResults = search.length >= 2 && (!items || items.length === 0);

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={handleInputChange}
        onFocus={() => search.length >= 2 && setIsOpen(true)}
        placeholder={placeholder}
        className={`field-input ${className}`}
        autoComplete="off"
      />

      {isOpen && (items?.length || hasNoResults) && (
        <div
          ref={dropdownRef}
          className="absolute z-50 left-0 right-0 mt-1 bg-surface border border-rule rounded-DEFAULT
                     shadow-modal max-h-72 overflow-y-auto"
        >
          {items && items.length > 0 && (
            <>
              <div className="eyebrow px-4 py-2.5 bg-paper-deep border-b border-rule">
                Catalog · {items.length} match{items.length === 1 ? '' : 'es'}
              </div>
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSelectItem(item)}
                  className="w-full text-left px-4 py-3 hover:bg-paper-deep
                             border-b border-rule-soft last:border-b-0 transition-colors"
                >
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-ink text-sm">{item.name}</span>
                        {item.alias && (
                          <span className="text-2xs font-mono text-oxblood bg-oxblood-wash px-1.5 py-0.5 rounded-sm">
                            @{item.alias}
                          </span>
                        )}
                      </div>
                      {item.description && (
                        <div className="text-xs text-ink-muted mt-1 line-clamp-1">
                          {item.description}
                        </div>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <div className="font-mono text-sm text-ink tabular">{formatRate(item.default_rate)}</div>
                      <div className="text-2xs text-ink-muted uppercase tracking-eyebrow">/{item.unit}</div>
                    </div>
                  </div>
                </button>
              ))}
            </>
          )}

          <button
            type="button"
            onClick={handleAddNewItem}
            className="w-full text-left px-4 py-3 hover:bg-status-paid-wash
                       border-t border-rule bg-paper-deep transition-colors group"
          >
            <div className="flex items-center gap-3 text-status-paid">
              <Plus size={14} strokeWidth={2} className="shrink-0" />
              <div className="text-sm">
                <span className="font-medium">Add</span>
                <span className="font-mono mx-1 text-ink">"{search}"</span>
                <span className="font-medium">to catalog</span>
                <div className="text-2xs uppercase tracking-eyebrow text-ink-muted mt-0.5">
                  Save for future invoices
                </div>
              </div>
            </div>
          </button>
        </div>
      )}

      {/* Add Item Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]"
               onClick={() => { setShowAddModal(false); resetForm(); }} />

          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-lg w-full
                          shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />

            <div className="p-8">
              <button
                onClick={() => { setShowAddModal(false); resetForm(); }}
                className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted transition-colors"
                aria-label="Close"
              >
                <X size={20} strokeWidth={1.5} />
              </button>

              <div className="mb-6">
                <div className="page-eyebrow">New entry</div>
                <h3 className="page-title !text-2xl">Add to your catalog</h3>
              </div>

              <form onSubmit={handleCreateItem} className="space-y-4">
                <div>
                  <label className="field-label">Name *</label>
                  <input
                    type="text"
                    required
                    value={newItemForm.name}
                    onChange={(e) => setNewItemForm({ ...newItemForm, name: e.target.value })}
                    className="field-input"
                    placeholder="e.g., Legal Consultation"
                    autoFocus
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Alias</label>
                    <input
                      type="text"
                      value={newItemForm.alias}
                      onChange={(e) => setNewItemForm({ ...newItemForm, alias: e.target.value })}
                      className="field-input font-mono"
                      placeholder="consult"
                    />
                  </div>
                  <div>
                    <label className="field-label">HSN/SAC</label>
                    <input
                      type="text"
                      value={newItemForm.hsn_code}
                      onChange={(e) => setNewItemForm({ ...newItemForm, hsn_code: e.target.value })}
                      className="field-input font-mono"
                      placeholder="998231"
                    />
                  </div>
                </div>

                <div>
                  <label className="field-label">Description (printed on invoice)</label>
                  <input
                    type="text"
                    value={newItemForm.description}
                    onChange={(e) => setNewItemForm({ ...newItemForm, description: e.target.value })}
                    className="field-input"
                    placeholder="Description shown on invoice"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Default rate (₹)</label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={newItemForm.default_rate}
                      onChange={(e) => setNewItemForm({
                        ...newItemForm,
                        default_rate: parseFloat(e.target.value) || 0,
                      })}
                      className="field-input font-mono tabular"
                    />
                  </div>
                  <div>
                    <label className="field-label">Unit</label>
                    <select
                      value={newItemForm.unit}
                      onChange={(e) => setNewItemForm({ ...newItemForm, unit: e.target.value })}
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

                <div className="flex gap-3 pt-3">
                  <button
                    type="button"
                    onClick={() => { setShowAddModal(false); resetForm(); }}
                    className="btn-ghost flex-1"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="btn-primary flex-1"
                  >
                    {createMutation.isPending ? 'Adding…' : 'Add & select'}
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
