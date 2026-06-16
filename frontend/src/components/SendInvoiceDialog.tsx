import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, Invoice } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { renderEmail, renderWhatsApp } from '../lib/messageTemplates';
import { X, Mail, MessageCircle, Send, AlertTriangle, Link2, Check } from 'lucide-react';

interface Props {
  invoice: Invoice | null;
  isOpen: boolean;
  onClose: () => void;
}

type Channel = 'email' | 'whatsapp';

/**
 * Send an invoice to its client over email or WhatsApp. Pre-fills the message
 * from the firm template, lets the user tweak it, then posts to /send.
 * Email is sent server-side; WhatsApp opens a wa.me deep-link.
 */
export default function SendInvoiceDialog({ invoice, isOpen, onClose }: Props) {
  const { firm } = useAuth();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [channel, setChannel] = useState<Channel>('email');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Recipient availability drives which channels are allowed.
  const [clientEmail, setClientEmail] = useState<string | undefined>();
  const [clientPhone, setClientPhone] = useState<string | undefined>();

  useEffect(() => {
    if (!isOpen || !invoice) return;
    setError(null);
    setBusy(false);
    setCopied(false);
    // Pre-fill message from templates.
    const email = renderEmail(invoice, firm);
    setSubject(email.subject);

    // Fetch the client to know which channels are available + show recipient.
    let cancelled = false;
    (async () => {
      try {
        const client = await api.getClient(invoice.client_id);
        if (cancelled) return;
        setClientEmail(client.email);
        setClientPhone(client.phone);
        // Default to a channel the client can actually receive on.
        const initial: Channel = client.email ? 'email' : client.phone ? 'whatsapp' : 'email';
        setChannel(initial);
        setBody(initial === 'email' ? email.body : renderWhatsApp(invoice, firm));
      } catch {
        // Non-fatal: keep email defaults.
        setBody(email.body);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, invoice]);

  // When the user switches channel, swap the pre-filled message.
  const switchChannel = (next: Channel) => {
    if (!invoice) return;
    setChannel(next);
    setError(null);
    if (next === 'email') {
      const email = renderEmail(invoice, firm);
      setSubject(email.subject);
      setBody(email.body);
    } else {
      setBody(renderWhatsApp(invoice, firm));
    }
  };

  if (!isOpen || !invoice) return null;

  const recipientMissing =
    (channel === 'email' && !clientEmail) || (channel === 'whatsapp' && !clientPhone);

  const handleCopyLink = async () => {
    if (!invoice) return;
    setError(null);
    try {
      const { link } = await api.getInvoiceShareLink(invoice.id, window.location.origin);
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      showToast('Shareable link copied to clipboard');
    } catch (e) {
      showToast('Failed to copy link', 'error');
      setError(e instanceof Error ? e.message : 'Failed to copy link');
    }
  };

  const handleSend = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.sendInvoice(invoice.id, {
        channel,
        ...(channel === 'email' ? { subject, body } : { body }),
        base_url: window.location.origin,
      });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      if (channel === 'whatsapp' && result.whatsapp_url) {
        window.open(result.whatsapp_url, '_blank', 'noopener');
      }
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to send');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={onClose} />

      <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-2xl w-full
                      max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
        <div className="h-[3px] bg-oxblood" />

        <div className="p-8">
          <button
            onClick={onClose}
            className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted transition-colors"
            aria-label="Close"
          >
            <X size={20} strokeWidth={1.5} />
          </button>

          <div className="mb-6">
            <div className="page-eyebrow">Send invoice</div>
            <h2 className="page-title !text-2xl">{invoice.invoice_number}</h2>
          </div>

          {/* Channel tabs */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => switchChannel('email')}
              className={channel === 'email' ? 'btn-primary' : 'btn-ghost'}
            >
              <Mail size={14} strokeWidth={2} />
              <span>Email</span>
            </button>
            <button
              onClick={() => switchChannel('whatsapp')}
              className={channel === 'whatsapp' ? 'btn-primary' : 'btn-ghost'}
            >
              <MessageCircle size={14} strokeWidth={2} />
              <span>WhatsApp</span>
            </button>
          </div>

          {/* Recipient line */}
          <div className="mb-4 text-sm text-ink-muted">
            To:{' '}
            <span className="font-mono text-ink">
              {channel === 'email' ? (clientEmail || '—') : (clientPhone || '—')}
            </span>
          </div>

          {recipientMissing && (
            <div className="mb-4 flex items-start gap-2 text-sm text-oxblood bg-oxblood-wash
                            px-3 py-2 rounded-sm">
              <AlertTriangle size={14} strokeWidth={2} className="shrink-0 mt-0.5" />
              <span>
                This client has no {channel === 'email' ? 'email address' : 'phone number'} on file.
                Add one on the client, or use the other channel.
              </span>
            </div>
          )}

          {/* Message */}
          {channel === 'email' && (
            <div className="mb-4">
              <label className="field-label">Subject</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="field-input"
              />
            </div>
          )}
          <div className="mb-2">
            <label className="field-label">{channel === 'email' ? 'Message' : 'WhatsApp message'}</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={channel === 'email' ? 8 : 5}
              className="field-textarea font-mono text-xs"
            />
          </div>
          <p className="text-2xs text-ink-faint mb-6">
            <code>{'{invoice_link}'}</code> is replaced with a secure link to the invoice when sent.
            {channel === 'whatsapp' && ' WhatsApp opens with this message pre-filled — you tap send.'}
          </p>

          {error && (
            <div className="mb-4 text-sm text-oxblood bg-oxblood-wash px-3 py-2 rounded-sm">{error}</div>
          )}

          <div className="flex gap-3 items-center pt-4 border-t border-rule">
            <button
              type="button"
              onClick={handleCopyLink}
              className="btn-ghost"
              title="Copy a shareable link to this invoice"
            >
              {copied ? <Check size={14} strokeWidth={2} /> : <Link2 size={14} strokeWidth={2} />}
              <span>{copied ? 'Copied' : 'Copy link'}</span>
            </button>
            <div className="flex-1" />
            <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
            <button
              type="button"
              onClick={handleSend}
              disabled={busy || recipientMissing}
              className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Send size={14} strokeWidth={2} />
              <span>
                {busy ? 'Sending…' : channel === 'email' ? 'Send email' : 'Open WhatsApp'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
