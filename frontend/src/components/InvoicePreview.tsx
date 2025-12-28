import { Invoice } from '../api';
import { useAuth } from '../contexts/AuthContext';

interface InvoicePreviewProps {
    invoice: Invoice | null;
    isOpen: boolean;
    onClose: () => void;
}

export default function InvoicePreview({ invoice, isOpen, onClose }: InvoicePreviewProps) {
    const { firm } = useAuth();

    if (!isOpen || !invoice) return null;

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 2,
        }).format(amount);
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-IN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    };

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
            {/* Backdrop */}
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose}></div>

            {/* Modal */}
            <div className="flex min-h-full items-center justify-center p-4">
                <div className="relative transform overflow-hidden rounded-lg bg-white shadow-xl transition-all w-full max-w-4xl max-h-[90vh] overflow-y-auto">
                    {/* Header */}
                    <div className="flex items-center justify-between p-4 border-b border-gray-200 sticky top-0 bg-white z-10">
                        <h3 className="text-lg font-semibold text-gray-900" id="modal-title">
                            Invoice Preview - {invoice.invoice_number}
                        </h3>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-500 focus:outline-none"
                        >
                            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Invoice Content */}
                    <div className="p-8 bg-white">
                        {/* Invoice Header */}
                        <div className="border-b-2 border-yellow-500 pb-6 mb-6">
                            <div className="flex justify-between items-start">
                                <div>
                                    <h1 className="text-2xl font-bold text-gray-900">{firm?.firm_name || 'Your Firm Name'}</h1>
                                    <p className="text-sm text-gray-600 whitespace-pre-line mt-1">{firm?.firm_address}</p>
                                    {firm?.firm_phone && <p className="text-sm text-gray-600">Tel: {firm.firm_phone}</p>}
                                    {firm?.firm_email && <p className="text-sm text-gray-600">Email: {firm.firm_email}</p>}
                                </div>
                                <div className="text-right">
                                    <h2 className="text-3xl font-bold text-yellow-600">INVOICE</h2>
                                    <p className="text-lg font-semibold mt-2">{invoice.invoice_number}</p>
                                    <p className="text-sm text-gray-600">Date: {formatDate(invoice.invoice_date)}</p>
                                    {invoice.due_date && (
                                        <p className="text-sm text-gray-600">Due: {formatDate(invoice.due_date)}</p>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Bill To */}
                        <div className="mb-6">
                            <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Bill To</h3>
                            <p className="text-lg font-semibold text-gray-900">{invoice.client_name}</p>
                            {invoice.short_desc && (
                                <p className="text-sm text-gray-600 mt-1">{invoice.short_desc}</p>
                            )}
                        </div>

                        {/* Line Items Table */}
                        <div className="mb-6">
                            <table className="w-full">
                                <thead>
                                    <tr className="bg-gray-100">
                                        <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Description</th>
                                        <th className="text-right py-3 px-4 text-sm font-semibold text-gray-700">Qty</th>
                                        <th className="text-right py-3 px-4 text-sm font-semibold text-gray-700">Rate</th>
                                        <th className="text-right py-3 px-4 text-sm font-semibold text-gray-700">Amount</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {invoice.items?.map((item, index) => (
                                        <tr key={index} className="border-b border-gray-200">
                                            <td className="py-3 px-4 text-sm text-gray-800">{item.description}</td>
                                            <td className="py-3 px-4 text-sm text-gray-800 text-right">{item.quantity}</td>
                                            <td className="py-3 px-4 text-sm text-gray-800 text-right">{formatCurrency(item.rate)}</td>
                                            <td className="py-3 px-4 text-sm text-gray-800 text-right">{formatCurrency(item.amount)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Totals */}
                        <div className="flex justify-end mb-6">
                            <div className="w-64">
                                <div className="flex justify-between py-2 border-b border-gray-200">
                                    <span className="text-sm text-gray-600">Subtotal</span>
                                    <span className="text-sm font-medium">{formatCurrency(invoice.subtotal)}</span>
                                </div>
                                <div className="flex justify-between py-2 border-b border-gray-200">
                                    <span className="text-sm text-gray-600">Tax ({invoice.tax_rate}%)</span>
                                    <span className="text-sm font-medium">{formatCurrency(invoice.tax_amount)}</span>
                                </div>
                                <div className="flex justify-between py-3 bg-yellow-50 px-3 rounded">
                                    <span className="text-lg font-bold text-gray-900">Total</span>
                                    <span className="text-lg font-bold text-yellow-600">{formatCurrency(invoice.total)}</span>
                                </div>
                            </div>
                        </div>

                        {/* Status Badge */}
                        <div className="flex justify-center mb-6">
                            <span className={`px-4 py-2 rounded-full text-sm font-semibold uppercase ${invoice.status === 'paid' ? 'bg-green-100 text-green-800' :
                                    invoice.status === 'sent' ? 'bg-blue-100 text-blue-800' :
                                        invoice.status === 'void' ? 'bg-red-100 text-red-800' :
                                            'bg-gray-100 text-gray-800'
                                }`}>
                                {invoice.status}
                            </span>
                        </div>

                        {/* Banking Details */}
                        {firm?.bank_name && (
                            <div className="bg-gray-50 p-4 rounded-lg mb-6">
                                <h4 className="text-sm font-semibold text-gray-700 mb-2">Payment Details</h4>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    <p><span className="text-gray-500">Bank:</span> {firm.bank_name}</p>
                                    <p><span className="text-gray-500">A/C:</span> {firm.account_number}</p>
                                    <p><span className="text-gray-500">IFSC:</span> {firm.ifsc_code}</p>
                                    {firm.upi_id && <p><span className="text-gray-500">UPI:</span> {firm.upi_id}</p>}
                                </div>
                            </div>
                        )}

                        {/* Terms */}
                        {firm?.billing_terms && (
                            <div className="text-xs text-gray-500 mt-8 pt-4 border-t border-gray-200">
                                <h5 className="font-semibold mb-1">Terms & Conditions</h5>
                                <p className="whitespace-pre-line">{firm.billing_terms}</p>
                            </div>
                        )}
                    </div>

                    {/* Footer Actions */}
                    <div className="flex justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50 sticky bottom-0">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
