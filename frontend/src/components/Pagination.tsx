import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

/**
 * Editorial page navigator. Renders nothing when there's a single page of data.
 */
export default function Pagination({ page, totalPages, total, pageSize, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between flex-wrap gap-4 mt-6">
      <span className="text-xs text-ink-muted tabular">
        Showing <span className="text-ink font-mono">{first}</span>–
        <span className="text-ink font-mono">{last}</span> of{' '}
        <span className="text-ink font-mono">{total}</span>
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="btn-secondary !px-3 disabled:opacity-40 disabled:cursor-not-allowed"
          title="Previous page"
        >
          <ChevronLeft size={14} strokeWidth={2} />
          <span>Prev</span>
        </button>
        <span className="text-xs uppercase tracking-eyebrow text-ink-muted px-2">
          Page <span className="text-ink font-mono">{page}</span> / <span className="text-ink font-mono">{totalPages}</span>
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="btn-secondary !px-3 disabled:opacity-40 disabled:cursor-not-allowed"
          title="Next page"
        >
          <span>Next</span>
          <ChevronRight size={14} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}
