import { Invoice } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { X } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

interface InvoicePreviewProps {
  invoice: Invoice | null;
  isOpen: boolean;
  onClose: () => void;
}

const statusPill: Record<string, string> = {
  draft:   'pill-draft',
  sent:    'pill-pending',
  paid:    'pill-paid',
  void:    'pill-overdue',
};

const formatINR = (amount: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(amount);

const formatDate = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString('en-IN', {
    year: 'numeric', month: 'long', day: 'numeric',
  });

export default function InvoicePreview({ invoice, isOpen, onClose }: InvoicePreviewProps) {
  const { firm } = useAuth();
  if (!isOpen || !invoice) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto animate-fade-in" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div className="fixed inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={onClose} />

      <div className="relative flex min-h-full items-start justify-center p-4 sm:p-8">
        <div className="relative bg-surface border border-rule rounded-DEFAULT w-full max-w-4xl
                        shadow-modal animate-fade-up">
          {/* Sticky header */}
          <div className="sticky top-0 z-10 bg-surface border-b border-rule px-6 py-4 rounded-t-DEFAULT flex items-center justify-between">
            <div>
              <div className="eyebrow text-oxblood">Preview</div>
              <h3 className="font-mono text-base text-ink mt-0.5" id="modal-title">
                {invoice.invoice_number}
              </h3>
            </div>
            <button onClick={onClose}
                    className="text-ink-faint hover:text-ink-muted transition-colors p-1"
                    aria-label="Close">
              <X size={20} strokeWidth={1.5} />
            </button>
          </div>

          {/* Invoice body — designed to look like the actual printed invoice */}
          <div className="p-10 bg-surface">
            {/* Letterhead */}
            <div className="border-b-2 border-ink pb-6 mb-8 flex justify-between items-start gap-6">
              <div>
                <h1 className="font-display text-3xl text-ink leading-tight"
                    style={{ fontVariationSettings: '"opsz" 144, "wght" 600, "SOFT" 20' }}>
                  {firm?.firm_name || 'Your firm name'}
                </h1>
                {firm?.firm_address && (
                  <p className="text-sm text-ink-soft whitespace-pre-line mt-2">{firm.firm_address}</p>
                )}
                <div className="text-xs text-ink-muted mt-2 space-x-3">
                  {firm?.firm_phone && <span className="font-mono">{firm.firm_phone}</span>}
                  {firm?.firm_email && <span>{firm.firm_email}</span>}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="eyebrow text-oxblood">Invoice</div>
                <div className="font-mono text-2xl text-ink mt-1 tabular">{invoice.invoice_number}</div>
                <div className="text-xs text-ink-muted mt-3 space-y-0.5">
                  <div>Dated: <span className="font-mono">{formatDate(invoice.invoice_date)}</span></div>
                  {invoice.due_date && (
                    <div>Due: <span className="font-mono">{formatDate(invoice.due_date)}</span></div>
                  )}
                </div>
                <div className="mt-3">
                  <span className={statusPill[invoice.status] || 'pill-draft'}>{invoice.status}</span>
                </div>
              </div>
            </div>

            {/* Bill to */}
            <div className="mb-8">
              <div className="eyebrow mb-2">Bill to</div>
              <p className="font-display text-xl text-ink"
                 style={{ fontVariationSettings: '"opsz" 48, "wght" 500' }}>
                {invoice.client_name}
              </p>
              {invoice.short_desc && (
                <p className="text-sm text-ink-muted mt-2 italic">{invoice.short_desc}</p>
              )}
            </div>

            {/* Line items */}
            <table className="table-editorial mb-6">
              <thead>
                <tr>
                  <th>Description</th>
                  <th className="!text-right w-20">Qty</th>
                  <th className="!text-right w-28">Rate</th>
                  <th className="!text-right w-32">Amount</th>
                </tr>
              </thead>
              <tbody>
                {invoice.items?.map((item, index) => (
                  <tr key={index}>
                    <td className="text-ink">{item.description}</td>
                    <td className="!text-right font-mono tabular">{item.quantity}</td>
                    <td className="!text-right font-mono tabular">{formatINR(item.rate)}</td>
                    <td className="!text-right font-mono tabular">{formatINR(item.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Totals */}
            <div className="flex justify-end mb-8">
              <div className="w-72 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-ink-muted">Subtotal</span>
                  <span className="font-mono text-ink tabular">{formatINR(invoice.subtotal)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-ink-muted">Tax ({invoice.tax_rate}%)</span>
                  <span className="font-mono text-ink tabular">{formatINR(invoice.tax_amount)}</span>
                </div>
                <div className="hairline border-t-strong border-ink" />
                <div className="flex justify-between items-baseline pt-1">
                  <span className="eyebrow">Total</span>
                  <span
                    className="font-display text-2xl text-ink tabular"
                    style={{ fontVariationSettings: '"opsz" 144, "wght" 600, "SOFT" 20' }}
                  >
                    {formatINR(invoice.total)}
                  </span>
                </div>
              </div>
            </div>

            {/* Banking */}
            {firm?.bank_name && (
              <div className="bg-paper-deep border border-rule rounded-DEFAULT p-5 mb-6">
                <div className="eyebrow mb-3">Payment details</div>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-ink-muted">Bank</span>
                    <span className="text-ink">{firm.bank_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-muted">A/C</span>
                    <span className="font-mono text-ink">{firm.account_number}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-muted">IFSC</span>
                    <span className="font-mono text-ink">{firm.ifsc_code}</span>
                  </div>
                  {firm.upi_id && (
                    <div className="flex justify-between">
                      <span className="text-ink-muted">UPI</span>
                      <span className="font-mono text-ink">{firm.upi_id}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Scan-to-pay UPI QR (generated per invoice with the exact amount) */}
            {invoice.upi_uri && (
              <div className="flex flex-col items-center gap-1 mb-6">
                <QRCodeSVG value={invoice.upi_uri} size={120} />
                <span className="text-xs text-ink-muted">Scan to pay {formatINR(invoice.total)}</span>
              </div>
            )}

            {/* Terms */}
            {firm?.billing_terms && (
              <div className="pt-6 border-t border-rule">
                <div className="eyebrow mb-2">Terms &amp; conditions</div>
                <p className="text-xs text-ink-muted whitespace-pre-line leading-relaxed">
                  {firm.billing_terms}
                </p>
              </div>
            )}
          </div>

          {/* Sticky footer */}
          <div className="sticky bottom-0 bg-paper-deep border-t border-rule px-6 py-4 rounded-b-DEFAULT flex justify-end">
            <button onClick={onClose} className="btn-secondary">Close</button>
          </div>
        </div>
      </div>
    </div>
  );
}
