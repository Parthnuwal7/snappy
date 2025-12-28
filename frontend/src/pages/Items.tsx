import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Item } from '../api';

export default function Items() {
    const queryClient = useQueryClient();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingItem, setEditingItem] = useState<Item | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        alias: '',
        description: '',
        default_rate: 0,
        unit: 'hour',
        hsn_code: '',
    });

    const { data: items, isLoading } = useQuery({
        queryKey: ['items'],
        queryFn: () => api.getItems(),
    });

    const createMutation = useMutation({
        mutationFn: api.createItem,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['items'] });
            closeModal();
        },
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: number; data: Partial<Item> }) =>
            api.updateItem(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['items'] });
            closeModal();
        },
    });

    const deleteMutation = useMutation({
        mutationFn: api.deleteItem,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['items'] });
        },
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
            setFormData({
                name: '',
                alias: '',
                description: '',
                default_rate: 0,
                unit: 'hour',
                hsn_code: '',
            });
        }
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setEditingItem(null);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (editingItem) {
            updateMutation.mutate({ id: editingItem.id, data: formData });
        } else {
            createMutation.mutate(formData);
        }
    };

    const handleDelete = (id: number) => {
        if (confirm('Are you sure you want to deactivate this item?')) {
            deleteMutation.mutate(id);
        }
    };

    const formatRate = (rate: number) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 0,
        }).format(rate);
    };

    return (
        <div className="p-8">
            <div className="mb-8 flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Items & Services</h1>
                    <p className="text-gray-600 mt-1">Manage your service/product catalog for quick invoicing</p>
                </div>
                <button
                    onClick={() => openModal()}
                    className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
                >
                    + Add Item
                </button>
            </div>

            {/* Items Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {isLoading ? (
                    <div className="col-span-full flex justify-center py-12">
                        <div className="spinner"></div>
                    </div>
                ) : items && items.length > 0 ? (
                    items.map((item) => (
                        <div key={item.id} className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                            <div className="flex justify-between items-start mb-3">
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900">{item.name}</h3>
                                    {item.alias && (
                                        <span className="text-sm text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                                            @{item.alias}
                                        </span>
                                    )}
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => openModal(item)}
                                        className="text-primary-600 hover:text-primary-800 text-sm"
                                    >
                                        Edit
                                    </button>
                                    <button
                                        onClick={() => handleDelete(item.id)}
                                        className="text-red-600 hover:text-red-800 text-sm"
                                    >
                                        Delete
                                    </button>
                                </div>
                            </div>

                            {item.description && (
                                <p className="text-sm text-gray-600 mb-3 line-clamp-2">{item.description}</p>
                            )}

                            <div className="flex justify-between items-center pt-3 border-t">
                                <div>
                                    <span className="text-2xl font-bold text-gray-900">{formatRate(item.default_rate)}</span>
                                    <span className="text-sm text-gray-500 ml-1">/{item.unit}</span>
                                </div>
                                {item.hsn_code && (
                                    <span className="text-xs text-gray-500">HSN: {item.hsn_code}</span>
                                )}
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="col-span-full text-center py-12 text-gray-500">
                        <p className="text-lg mb-4">No items yet</p>
                        <p className="text-sm mb-4">Create items to quickly add them to invoices</p>
                        <button
                            onClick={() => openModal()}
                            className="text-primary-600 hover:text-primary-800 font-medium"
                        >
                            Add your first item
                        </button>
                    </div>
                )}
            </div>

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
                        <h2 className="text-2xl font-bold mb-6">
                            {editingItem ? 'Edit Item' : 'New Item'}
                        </h2>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Name *</label>
                                <input
                                    type="text"
                                    required
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                    placeholder="e.g., Legal Consultation"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Alias (for quick search)
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.alias}
                                        onChange={(e) => setFormData({ ...formData, alias: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                        placeholder="e.g., consult, lc"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">HSN/SAC Code</label>
                                    <input
                                        type="text"
                                        value={formData.hsn_code}
                                        onChange={(e) => setFormData({ ...formData, hsn_code: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                        placeholder="e.g., 998231"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    rows={3}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                    placeholder="Description that appears on the invoice"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Default Rate (₹)</label>
                                    <input
                                        type="number"
                                        min="0"
                                        step="0.01"
                                        value={formData.default_rate}
                                        onChange={(e) => setFormData({ ...formData, default_rate: parseFloat(e.target.value) || 0 })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Unit</label>
                                    <select
                                        value={formData.unit}
                                        onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
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

                            <div className="flex gap-4 pt-4">
                                <button
                                    type="button"
                                    onClick={closeModal}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                                >
                                    {editingItem ? 'Update Item' : 'Create Item'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
