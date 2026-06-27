import { api, LegalFeedItem } from '../api';

export default function NewsCard({ item, onNotInterested }: {
  item: LegalFeedItem;
  onNotInterested: (id: number) => void;
}) {
  const open = () => { void api.postLegalFeedEvent(item.id, 'click'); };
  const notInterested = () => {
    void api.postLegalFeedEvent(item.id, 'not_interested');
    onNotInterested(item.id);
  };
  return (
    <div className="break-inside-avoid mb-4 border border-rule rounded-lg p-3 bg-paper">
      <div className="flex items-center gap-2 mb-1">
        <span className="eyebrow text-ink-faint">{item.source_name}</span>
        {item.published_at && (
          <span className="text-2xs text-ink-muted ml-auto">
            {new Date(item.published_at).toLocaleDateString()}
          </span>
        )}
      </div>
      <h3 className="text-ink font-medium leading-snug mb-1">{item.headline || item.title}</h3>
      {(item.tldr || item.summary) && (
        <p className="text-sm text-ink-soft mb-2">{item.tldr || item.summary}</p>
      )}
      <div className="flex items-center justify-between">
        <a href={item.source_url} target="_blank" rel="noopener noreferrer" onClick={open}
          className="text-sm text-oxblood hover:underline">Read at source ↗</a>
        <button onClick={notInterested}
          className="text-2xs text-ink-faint hover:text-ink" title="Not interested">
          Not interested ✕
        </button>
      </div>
    </div>
  );
}
