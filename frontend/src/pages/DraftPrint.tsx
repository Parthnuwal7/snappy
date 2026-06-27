import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export default function DraftPrint() {
  const { id } = useParams();
  const { data: draft, isLoading } = useQuery({ queryKey: ['draft', Number(id)], queryFn: () => api.getDraft(Number(id)), enabled: !!id });
  useEffect(() => { if (!isLoading && draft) { const t = setTimeout(() => window.print(), 400); return () => clearTimeout(t); } }, [isLoading, draft]);
  if (!draft) return null;
  return (
    <div className="max-w-3xl mx-auto p-12 bg-white text-ink min-h-screen">
      <button onClick={() => window.print()} className="btn-primary print:hidden mb-6">Print</button>
      <h1 className="text-xl font-display mb-6">{draft.title}</h1>
      <div className="prose prose-sm max-w-none [&_table]:border-collapse [&_td]:border [&_td]:border-ink/30 [&_td]:p-1 [&_th]:border [&_th]:border-ink/30 [&_th]:p-1" dangerouslySetInnerHTML={{ __html: draft.body }} />
    </div>
  );
}
