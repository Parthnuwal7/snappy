import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Client } from '../api';
import { Plus, Search, Mail, Phone, Building2, Pencil, Trash2, X } from 'lucide-react';

const EMPTY_FORM = {
  name: '',
  email: '',
  phone: '',
  address: '',
  tax_id: '',
  default_tax_rate: 18,
  notes: '',
};

export default function Clients() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [formData, setFormData] = useState(EMPTY_FORM);

  const { data: clients, isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
  });

  const filteredClients = useMemo(() => {
    if (!clients) return [];
    if (!searchQuery.trim()) return clients;
    const q = searchQuery.toLowerCase();
    return clients.filter((c) =>
      c.name.toLowerCase().includes(q) ||
      c.address?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) ||
      c.phone?.includes(q)
    );
  }, [clients, searchQuery]);

  const createMutation = useMutation({
    mutationFn: api.createClient,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['clients'] }); closeModal(); },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Client> }) =>
      api.updateClient(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['clients'] }); closeModal(); },
  });
  const deleteMutation = useMutation({
    mutationFn: api.deleteClient,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clients'] }),
  });

  const openModal = (client?: Client) => {
    if (client) {
      setEditingClient(client);
      setFormData({
        name: client.name,
        email: client.email || '',
        phone: client.phone || '',
        address: client.address || '',
        tax_id: client.tax_id || '',
        default_tax_rate: client.default_tax_rate,
        notes: client.notes || '',
      });
    } else {
      setEditingClient(null);
      setFormData(EMPTY_FORM);
    }
    setIsModalOpen(true);
  };

  const closeModal = () => { setIsModalOpen(false); setEditingClient(null); };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingClient) updateMutation.mutate({ id: editingClient.id, data: formData });
    else createMutation.mutate(formData);
  };

  const handleDelete = (id: number) => {
    if (confirm('Delete this client? This cannot be undone.')) deleteMutation.mutate(id);
  };

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="flex items-end justify-between flex-wrap gap-6 mb-10">
        <div>
          <div className="page-eyebrow">Folio III · Register</div>
          <h1 className="page-title">Clients</h1>
          <p className="page-subtitle">
            Your roster of represented parties and counterparties.
          </p>
        </div>
        <button onClick={() => openModal()} className="btn-primary">
          <Plus size={14} strokeWidth={2} />
          <span>New client</span>
        </button>
      </header>

      {/* Search */}
      <div className="card p-4 mb-6 flex items-center gap-3">
        <Search size={16} strokeWidth={1.5} className="text-ink-faint shrink-0 ml-2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by name, address, email, or phone…"
          className="flex-1 bg-transparent border-none outline-none text-sm placeholder:text-ink-faint"
        />
        {searchQuery && (
          <span className="text-xs text-ink-muted tabular shrink-0 mr-2">
            {filteredClients.length} match{filteredClients.length === 1 ? '' : 'es'}
          </span>
        )}
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="card p-16 flex justify-center"><div className="spinner" /></div>
      ) : filteredClients && filteredClients.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-rule border border-rule">
          {filteredClients.map((client) => (
            <article key={client.id} className="bg-surface p-6 hover:bg-paper-deep/50 transition-colors group">
              <header className="flex items-start justify-between gap-3 mb-4">
                <h3 className="font-display text-xl text-ink leading-snug"
                    style={{ fontVariationSettings: '"opsz" 48, "wght" 500' }}>
                  {client.name}
                </h3>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => openModal(client)}
                    className="p-1.5 text-ink-muted hover:text-ink hover:bg-paper-deep rounded-sm transition-colors"
                    title="Edit"
                  >
                    <Pencil size={13} strokeWidth={1.75} />
                  </button>
                  <button
                    onClick={() => handleDelete(client.id)}
                    className="p-1.5 text-ink-muted hover:text-oxblood hover:bg-oxblood-wash rounded-sm transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={13} strokeWidth={1.75} />
                  </button>
                </div>
              </header>

              <div className="space-y-2 text-sm text-ink-soft">
                {client.email && (
                  <div className="flex items-center gap-2.5">
                    <Mail size={13} strokeWidth={1.5} className="text-ink-faint shrink-0" />
                    <span className="truncate">{client.email}</span>
                  </div>
                )}
                {client.phone && (
                  <div className="flex items-center gap-2.5">
                    <Phone size={13} strokeWidth={1.5} className="text-ink-faint shrink-0" />
                    <span className="font-mono">{client.phone}</span>
                  </div>
                )}
                {client.tax_id && (
                  <div className="flex items-center gap-2.5">
                    <Building2 size={13} strokeWidth={1.5} className="text-ink-faint shrink-0" />
                    <span className="font-mono text-xs">{client.tax_id}</span>
                  </div>
                )}
              </div>

              <div className="hairline pt-3 mt-4 flex items-center justify-between">
                <span className="eyebrow">Default tax</span>
                <span className="font-mono text-xs text-ink tabular">{client.default_tax_rate}%</span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="card p-16 text-center">
          <div className="page-eyebrow">Empty register</div>
          <h2 className="section-title mt-2">No clients yet</h2>
          <p className="text-base text-ink-muted mt-3">
            Add your first client to start sending invoices.
          </p>
          <button onClick={() => openModal()} className="btn-primary mt-6">
            <Plus size={14} strokeWidth={2} />
            <span>Add first client</span>
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
                <div className="page-eyebrow">{editingClient ? 'Edit entry' : 'New entry'}</div>
                <h2 className="page-title !text-2xl">
                  {editingClient ? client_displayName(editingClient) : 'New client'}
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
                    autoFocus
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Email</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="field-input"
                    />
                  </div>
                  <div>
                    <label className="field-label">Phone</label>
                    <input
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="field-input font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="field-label">Address</label>
                  <textarea
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    rows={3}
                    className="field-textarea"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Tax ID / GSTIN</label>
                    <input
                      type="text"
                      value={formData.tax_id}
                      onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
                      className="field-input font-mono"
                    />
                  </div>
                  <div>
                    <label className="field-label">Default tax rate (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.default_tax_rate}
                      onChange={(e) => setFormData({ ...formData, default_tax_rate: parseFloat(e.target.value) })}
                      className="field-input font-mono tabular"
                    />
                  </div>
                </div>

                <div>
                  <label className="field-label">Notes</label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                    className="field-textarea"
                  />
                </div>

                <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                  <button type="button" onClick={closeModal} className="btn-ghost">Cancel</button>
                  <button
                    type="submit"
                    disabled={createMutation.isPending || updateMutation.isPending}
                    className="btn-primary"
                  >
                    {editingClient ? 'Save changes' : 'Create client'}
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

function client_displayName(c: Client) { return c.name; }
