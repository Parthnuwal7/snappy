import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Item } from '../api';

interface ItemAutocompleteProps {
    value: string;
    onChange: (value: string) => void;
    onSelectItem: (item: Item) => void;
    placeholder?: string;
    className?: string;
}

export default function ItemAutocomplete({
    value,
    onChange,
    onSelectItem,
    placeholder = 'Search or type description...',
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

    // Debounced search query
    const { data: items } = useQuery({
        queryKey: ['items-search', search],
        queryFn: () => api.getItems(search, true),
        enabled: search.length >= 2,
        staleTime: 5000,
    });

    // Create item mutation
    const createMutation = useMutation({
        mutationFn: api.createItem,
        onSuccess: (newItem) => {
            console.log('Item created successfully:', newItem);
            queryClient.invalidateQueries({ queryKey: ['items'] });
            queryClient.invalidateQueries({ queryKey: ['items-search'] });
            setShowAddModal(false);
            // Auto-select the newly created item
            onChange(newItem.description || newItem.name);
            onSelectItem(newItem);
            resetForm();
        },
        onError: (error) => {
            console.error('Failed to create item:', error);
            alert(`Failed to create item: ${error.message}`);
        },
    });

    const resetForm = () => {
        setNewItemForm({
            name: '',
            alias: '',
            description: '',
            default_rate: 0,
            unit: 'hour',
            hsn_code: '',
        });
    };

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target as Node) &&
                inputRef.current &&
                !inputRef.current.contains(event.target as Node)
            ) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = e.target.value;
        onChange(newValue);
        setSearch(newValue);
        setIsOpen(newValue.length >= 2);
    };

    const handleSelectItem = (item: Item) => {
        onChange(item.description || item.name);
        onSelectItem(item);
        setIsOpen(false);
        setSearch('');
    };

    const handleAddNewItem = () => {
        // Pre-fill the form with what the user typed
        setNewItemForm({
            ...newItemForm,
            name: search,
            description: search,
        });
        setShowAddModal(true);
        setIsOpen(false);
    };

    const handleCreateItem = (e: React.FormEvent) => {
        e.preventDefault();
        console.log('handleCreateItem called with form data:', newItemForm);
        if (!newItemForm.name.trim()) {
            console.log('Item name is empty, returning');
            return;
        }
        console.log('Calling createMutation.mutate...');
        createMutation.mutate(newItemForm);
    };

    const formatRate = (rate: number) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 0,
        }).format(rate);
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
                className={`w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 ${className}`}
                autoComplete="off"
            />

            {isOpen && (items?.length || hasNoResults) && (
                <div
                    ref={dropdownRef}
                    className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-72 overflow-y-auto"
                >
                    {items && items.length > 0 && (
                        <>
                            <div className="px-3 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b">
                                Quick select from catalog
                            </div>
                            {items.map((item) => (
                                <button
                                    key={item.id}
                                    type="button"
                                    onClick={() => handleSelectItem(item)}
                                    className="w-full text-left px-4 py-3 hover:bg-primary-50 border-b transition-colors"
                                >
                                    <div className="flex justify-between items-start">
                                        <div className="flex-1">
                                            <div className="font-medium text-gray-900">{item.name}</div>
                                            {item.alias && (
                                                <span className="text-xs text-primary-600 bg-primary-50 px-1.5 py-0.5 rounded">
                                                    @{item.alias}
                                                </span>
                                            )}
                                            {item.description && (
                                                <div className="text-sm text-gray-500 mt-0.5 line-clamp-1">{item.description}</div>
                                            )}
                                        </div>
                                        <div className="text-right ml-4">
                                            <div className="font-semibold text-gray-900">{formatRate(item.default_rate)}</div>
                                            <div className="text-xs text-gray-500">/{item.unit}</div>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </>
                    )}

                    {/* Add New Item Option */}
                    <button
                        type="button"
                        onClick={handleAddNewItem}
                        className="w-full text-left px-4 py-3 hover:bg-green-50 border-t bg-gray-50 transition-colors"
                    >
                        <div className="flex items-center gap-2 text-green-700">
                            <span className="text-lg">➕</span>
                            <div>
                                <div className="font-medium">Add "{search}" to catalog</div>
                                <div className="text-xs text-gray-500">Save for future invoices</div>
                            </div>
                        </div>
                    </button>
                </div>
            )}

            {/* Add Item Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100] p-4">
                    <div className="bg-white rounded-lg max-w-lg w-full p-6 shadow-xl">
                        <h3 className="text-xl font-bold mb-4">Add New Item</h3>
                        <form onSubmit={handleCreateItem} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                                <input
                                    type="text"
                                    required
                                    value={newItemForm.name}
                                    onChange={(e) => setNewItemForm({ ...newItemForm, name: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                    placeholder="e.g., Legal Consultation"
                                    autoFocus
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Alias (quick search)</label>
                                    <input
                                        type="text"
                                        value={newItemForm.alias}
                                        onChange={(e) => setNewItemForm({ ...newItemForm, alias: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                        placeholder="e.g., consult"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">HSN/SAC Code</label>
                                    <input
                                        type="text"
                                        value={newItemForm.hsn_code}
                                        onChange={(e) => setNewItemForm({ ...newItemForm, hsn_code: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                        placeholder="e.g., 998231"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Description (for invoice)</label>
                                <input
                                    type="text"
                                    value={newItemForm.description}
                                    onChange={(e) => setNewItemForm({ ...newItemForm, description: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                    placeholder="Description shown on invoice"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Default Rate (₹)</label>
                                    <input
                                        type="number"
                                        min="0"
                                        step="0.01"
                                        value={newItemForm.default_rate}
                                        onChange={(e) => setNewItemForm({ ...newItemForm, default_rate: parseFloat(e.target.value) || 0 })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Unit</label>
                                    <select
                                        value={newItemForm.unit}
                                        onChange={(e) => setNewItemForm({ ...newItemForm, unit: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
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

                            <div className="flex gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => { setShowAddModal(false); resetForm(); }}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={createMutation.isPending}
                                    className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                                >
                                    {createMutation.isPending ? 'Adding...' : 'Add & Select'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
