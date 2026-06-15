import { BarChart3 } from 'lucide-react';

export default function Reports() {
  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="mb-12">
        <div className="page-eyebrow">Folio V · Reports</div>
        <h1 className="page-title">Reports &amp; analytics</h1>
        <p className="page-subtitle">
          Detailed financial and practice reports.
        </p>
      </header>

      <div className="card p-16 text-center">
        <BarChart3 size={32} strokeWidth={1.25} className="mx-auto text-ink-faint mb-6" />
        <div className="eyebrow text-oxblood">In preparation</div>
        <h2 className="section-title mt-2">A fuller set of reports is being typeset</h2>
        <p className="text-base text-ink-muted mt-3 max-w-prose mx-auto">
          For now, the Dashboard carries the principal figures for your practice —
          trailing revenue, top clients, and outstanding receivables.
        </p>
      </div>
    </div>
  );
}
