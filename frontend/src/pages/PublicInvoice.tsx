import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, PublicInvoice as PublicInvoiceData } from '../api';
import { Download, FileText } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

const formatINR = (value?: number) =>
  '₹' + (value ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const formatDate = (date?: string) =>
  date ? new Date(date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

/**
 * Public, unauthenticated hosted invoice page. Reached via a signed link
 * (/i/:userId/:invoiceId/:sig). Renders a client-facing view + Download PDF.
 */
export default function PublicInvoice() {
  const { userId, invoiceId, sig } = useParams();
  const [invoice, setInvoice] = useState<PublicInvoiceData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!userId || !invoiceId || !sig) return;
    (async () => {
      try {
        setInvoice(await api.getPublicInvoice(userId, invoiceId, sig));
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Unable to load invoice');
      } finally {
        setLoading(false);
      }
    })();
  }, [userId, invoiceId, sig]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper-deep">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper-deep px-4">
        <div className="card p-12 text-center max-w-md">
          <div className="page-eyebrow">Unavailable</div>
          <h1 className="section-title mt-2">This invoice can't be shown</h1>
          <p className="text-base text-ink-muted mt-3">
            The link may be invalid or expired. Please request a new link from the sender.
          </p>
        </div>
      </div>
    );
  }

  const pdfUrl = api.publicPdfUrl(userId!, invoiceId!, sig!);

  // Fetch as a blob and trigger a real download. A plain cross-origin <a download>
  // is ignored by browsers (page and API are different origins), so it would
  // otherwise just open the PDF inline in a new tab.
  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await fetch(pdfUrl);
      if (!res.ok) throw new Error('Failed to fetch PDF');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Invoice_${invoice.invoice_number.replace(/\//g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      // Last resort: open it in a tab so the user still gets the PDF.
      window.open(pdfUrl, '_blank', 'noopener');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper-deep py-10 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="card overflow-hidden">
          <div className="h-[3px] bg-oxblood" />
          <div className="p-8">
            <div className="flex items-start justify-between flex-wrap gap-4">
              <div>
                <div className="page-eyebrow">Invoice</div>
                <h1 className="font-display text-3xl text-ink mt-1"
                    style={{ fontVariationSettings: '"opsz" 48, "wght" 500' }}>
                  {invoice.invoice_number}
                </h1>
                <p className="text-sm text-ink-muted mt-2">
                  Issued {formatDate(invoice.invoice_date)} · Due {formatDate(invoice.due_date)}
                </p>
              </div>
              {invoice.firm && (
                <div className="text-right">
                  <div className="font-display text-xl text-ink"
                       style={{ fontVariationSettings: '"opsz" 48, "wght" 500' }}>
                    {invoice.firm.firm_name}
                  </div>
                  {invoice.firm.firm_address && (
                    <div className="text-xs text-ink-muted mt-1 whitespace-pre-line">{invoice.firm.firm_address}</div>
                  )}
                  {invoice.firm.firm_email && (
                    <div className="text-xs text-ink-muted mt-1">{invoice.firm.firm_email}</div>
                  )}
                </div>
              )}
            </div>

            <div className="hairline my-6" />

            <div className="text-sm">
              <span className="eyebrow">Billed to</span>
              <div className="text-ink text-lg mt-1">{invoice.client_name}</div>
            </div>

            {invoice.short_desc && (
              <p className="text-sm text-ink-muted mt-4">{invoice.short_desc}</p>
            )}

            {/* Line items */}
            <div className="mt-8 overflow-x-auto">
              <table className="table-editorial">
                <thead>
                  <tr>
                    <th>Description</th>
                    <th className="!text-right">Qty</th>
                    <th className="!text-right">Rate</th>
                    <th className="!text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.items.map((it, i) => (
                    <tr key={i}>
                      <td className="text-ink">{it.description}</td>
                      <td className="text-right font-mono text-ink-muted tabular">{it.quantity}</td>
                      <td className="text-right font-mono text-ink-muted tabular">{formatINR(it.rate)}</td>
                      <td className="text-right font-mono text-ink tabular">{formatINR(it.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Totals */}
            <div className="mt-6 flex justify-end">
              <div className="w-full max-w-xs space-y-2 text-sm">
                <div className="flex justify-between text-ink-muted">
                  <span>Subtotal</span><span className="font-mono tabular">{formatINR(invoice.subtotal)}</span>
                </div>
                <div className="flex justify-between text-ink-muted">
                  <span>Tax ({invoice.tax_rate ?? 0}%)</span>
                  <span className="font-mono tabular">{formatINR(invoice.tax_amount)}</span>
                </div>
                <div className="hairline" />
                <div className="flex justify-between text-ink text-lg font-display"
                     style={{ fontVariationSettings: '"opsz" 48, "wght" 500' }}>
                  <span>Total</span><span className="tabular">{formatINR(invoice.total)}</span>
                </div>
              </div>
            </div>

            {/* Payment details */}
            {invoice.payment && (invoice.payment.upi_id || invoice.payment.account_number) && (
              <div className="mt-8 hairline pt-6">
                <span className="eyebrow">Payment</span>
                <div className="mt-2 text-sm text-ink-muted space-y-1">
                  {invoice.payment.upi_id && (
                    <div>UPI: <span className="font-mono text-ink">{invoice.payment.upi_id}</span></div>
                  )}
                  {invoice.payment.account_number && (
                    <div>
                      {invoice.payment.bank_name} · A/C{' '}
                      <span className="font-mono text-ink">{invoice.payment.account_number}</span>
                      {invoice.payment.ifsc_code && <> · IFSC <span className="font-mono text-ink">{invoice.payment.ifsc_code}</span></>}
                    </div>
                  )}
                </div>
                {invoice.payment.upi_uri && (
                  <div className="mt-4 flex flex-col items-center gap-1">
                    <QRCodeSVG value={invoice.payment.upi_uri} size={140} />
                    <span className="text-xs text-ink-muted">Scan to pay {formatINR(invoice.total)}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Download */}
        <div className="mt-6 flex items-center justify-center gap-4">
          <button onClick={handleDownload} disabled={downloading} className="btn-primary disabled:opacity-50">
            <Download size={14} strokeWidth={2} />
            <span>{downloading ? 'Preparing…' : 'Download PDF'}</span>
          </button>
        </div>

        <div className="mt-8 text-center text-2xs text-ink-faint flex items-center justify-center gap-1.5">
          <FileText size={11} strokeWidth={1.5} />
          <span>Powered by Snappy</span>
        </div>
      </div>
    </div>
  );
}
