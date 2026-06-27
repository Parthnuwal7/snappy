import { useEffect, useState } from 'react';
import { api, LegalFeedItem } from '../api';
import Pagination from '../components/Pagination';
import LegalFeedPersonalize from '../components/LegalFeedPersonalize';
import NewsCard from '../components/NewsCard';

const PAGE_SIZE = 20;
const FORYOU_PAGE = 30;

export default function LegalFeed() {
  const [forYou, setForYou] = useState<LegalFeedItem[]>([]);
  const [forYouOffset, setForYouOffset] = useState(0);
  const [forYouMore, setForYouMore] = useState(true);
  const [items, setItems] = useState<LegalFeedItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // For you: reset + load first page on mount / when prefs are saved.
  useEffect(() => {
    setForYouOffset(0);
    api.getLegalFeedForYou({ type: 'news', limit: FORYOU_PAGE, offset: 0 })
      .then((d) => { setForYou(d); setForYouMore(d.length === FORYOU_PAGE); })
      .catch(() => { setForYou([]); setForYouMore(false); });
  }, [refreshKey]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getLegalFeed({ page, type: 'news', page_size: PAGE_SIZE })
      .then((res) => { setItems(res.data); setTotalPages(res.total_pages || 1); setTotal(res.total); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [page]);

  const loadMore = async () => {
    const next = forYouOffset + FORYOU_PAGE;
    const more = await api.getLegalFeedForYou({ type: 'news', limit: FORYOU_PAGE, offset: next });
    setForYou((cur) => [...cur, ...more]);
    setForYouOffset(next);
    setForYouMore(more.length === FORYOU_PAGE);
  };

  const removeItem = (id: number) => {
    setForYou((cur) => cur.filter((i) => i.id !== id));
    setItems((cur) => cur.filter((i) => i.id !== id));
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="eyebrow text-ink-faint mb-1">Library</div>
          <h1 className="font-display text-3xl text-ink">Legal News</h1>
        </div>
        <button onClick={() => setShowPanel(true)}
          className="text-sm border border-rule rounded px-3 py-1.5 text-ink-soft hover:text-ink">
          Personalize
        </button>
      </div>

      {/* For you */}
      {forYou.length > 0 && (
        <section className="mb-8">
          <div className="eyebrow text-ink-faint mb-3">For you</div>
          <div className="columns-1 sm:columns-2 lg:columns-3 gap-4">
            {forYou.map((i) => <NewsCard key={`fy-${i.id}`} item={i} onNotInterested={removeItem} />)}
          </div>
          {forYouMore && (
            <button onClick={loadMore}
              className="mt-4 text-sm border border-rule rounded px-4 py-1.5 text-ink-soft hover:text-ink">
              Load more
            </button>
          )}
        </section>
      )}

      {/* Latest */}
      <div className="eyebrow text-ink-faint mb-3">Latest</div>

      {loading && <p className="text-ink-muted text-sm">Loading…</p>}
      {error && <p className="text-oxblood text-sm">Failed to load: {error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="text-ink-muted text-sm">No items yet. Check back soon.</p>
      )}

      <div className="columns-1 sm:columns-2 lg:columns-3 gap-4">
        {items.map((i) => <NewsCard key={i.id} item={i} onNotInterested={removeItem} />)}
      </div>

      <Pagination page={page} totalPages={totalPages} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />

      {showPanel && (
        <LegalFeedPersonalize courts={[]} onClose={() => setShowPanel(false)}
          onSaved={() => setRefreshKey((k) => k + 1)} />
      )}
    </div>
  );
}
