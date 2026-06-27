import { useEffect, useState } from 'react';
import { api, PRACTICE_AREAS, LegalFeedPreference } from '../api';

export default function LegalFeedPersonalize({
  courts, onClose, onSaved,
}: { courts: string[]; onClose: () => void; onSaved: () => void }) {
  const [topics, setTopics] = useState<string[]>([]);
  const [selCourts, setSelCourts] = useState<string[]>([]);
  const [phrases, setPhrases] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getLegalFeedPreferences().then((p) => {
      setTopics(Object.keys(p.topic_weights || {}));
      setSelCourts(p.courts || []);
      setPhrases((p.interest_phrases || []).join(', '));
    });
  }, []);

  const toggle = (list: string[], set: (v: string[]) => void, v: string) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const save = async () => {
    setSaving(true);
    const pref: LegalFeedPreference = {
      topic_weights: Object.fromEntries(topics.map((t) => [t, 1.0])),
      courts: selCourts,
      interest_phrases: phrases.split(',').map((s) => s.trim()).filter(Boolean),
    };
    await api.putLegalFeedPreferences(pref);
    setSaving(false);
    onSaved();
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-paper border border-rule rounded-lg p-6 max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
        <h2 className="font-display text-xl text-ink mb-4">Personalize your feed</h2>

        <div className="eyebrow text-ink-faint mb-2">Practice areas</div>
        <div className="flex flex-wrap gap-2 mb-4">
          {PRACTICE_AREAS.map((t) => (
            <button key={t} onClick={() => toggle(topics, setTopics, t)}
              className={['text-xs px-2 py-1 rounded border',
                topics.includes(t) ? 'bg-oxblood text-white border-oxblood' : 'border-rule text-ink-soft'].join(' ')}>
              {t}
            </button>
          ))}
        </div>

        <div className="eyebrow text-ink-faint mb-2">Courts</div>
        <div className="flex flex-wrap gap-2 mb-4">
          {courts.map((c) => (
            <button key={c} onClick={() => toggle(selCourts, setSelCourts, c)}
              className={['text-xs px-2 py-1 rounded border',
                selCourts.includes(c) ? 'bg-oxblood text-white border-oxblood' : 'border-rule text-ink-soft'].join(' ')}>
              {c}
            </button>
          ))}
        </div>

        <div className="eyebrow text-ink-faint mb-2">Specific interests (comma-separated)</div>
        <input value={phrases} onChange={(e) => setPhrases(e.target.value)}
          placeholder="e.g. GST input credit, anticipatory bail"
          className="w-full border border-rule rounded px-3 py-1.5 text-sm bg-paper text-ink mb-4" />

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="text-sm text-ink-soft px-3 py-1.5">Cancel</button>
          <button onClick={save} disabled={saving}
            className="text-sm bg-oxblood text-white rounded px-3 py-1.5 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
