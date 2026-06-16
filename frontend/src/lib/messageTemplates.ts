/**
 * Client-side message templating — mirrors the backend defaults so the Send
 * dialog can pre-fill subject/body/text. The server re-renders on send (and
 * resolves {invoice_link}, which the client cannot compute), so this is purely
 * for the editable preview.
 */
import { Invoice } from '../api';
import { Firm } from '../contexts/AuthContext';

export const DEFAULT_EMAIL_SUBJECT = 'Invoice {invoice_number} from {firm_name}';
export const DEFAULT_EMAIL_BODY =
  'Dear {client_name},\n\n' +
  'Please find attached invoice {invoice_number} for {total}, due {due_date}.\n' +
  'You can also view it online here: {invoice_link}\n\n' +
  'Thank you for your business.\n\n' +
  'Regards,\n{firm_name}';
export const DEFAULT_WHATSAPP =
  "Hi {client_name}, here's invoice {invoice_number} for {total} (due {due_date}): {invoice_link}";

export const PLACEHOLDERS = [
  'client_name', 'invoice_number', 'firm_name', 'total', 'due_date', 'invoice_link',
];

type Ctx = Record<string, string>;

/** Substitute known {placeholders}; leave unknown ones untouched. */
export function render(template: string, ctx: Ctx): string {
  return template.replace(/\{(\w+)\}/g, (match, key) =>
    key in ctx ? ctx[key] : match
  );
}

export function buildContext(invoice: Invoice, firm: Firm | null): Ctx {
  const total = `₹${Number(invoice.total ?? 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}`;
  return {
    client_name: invoice.client_name ?? '',
    invoice_number: invoice.invoice_number,
    firm_name: firm?.firm_name ?? '',
    total,
    due_date: invoice.due_date ?? 'on receipt',
    // Leave {invoice_link} as a literal token: the user can't compute the signed
    // link, and the server resolves this placeholder when it sends. Keeping it
    // verbatim means an edited message still gets the real link injected.
    invoice_link: '{invoice_link}',
  };
}

export function renderEmail(invoice: Invoice, firm: Firm | null) {
  const ctx = buildContext(invoice, firm);
  return {
    subject: render(firm?.email_subject_template || DEFAULT_EMAIL_SUBJECT, ctx),
    body: render(firm?.email_body_template || DEFAULT_EMAIL_BODY, ctx),
  };
}

export function renderWhatsApp(invoice: Invoice, firm: Firm | null) {
  const ctx = buildContext(invoice, firm);
  return render(firm?.whatsapp_template || DEFAULT_WHATSAPP, ctx);
}
