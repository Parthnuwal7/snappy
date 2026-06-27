import { useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import Link from '@tiptap/extension-link';
import TextAlign from '@tiptap/extension-text-align';
import Highlight from '@tiptap/extension-highlight';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import {
  Bold, Italic, Underline as U, List, ListOrdered, Heading1, Heading2,
  AlignLeft, AlignCenter, AlignRight, Link as LinkIcon, Highlighter, Table as TableIcon,
} from 'lucide-react';

interface MergeField { token: string; label: string; source: string }

export default function Editor({ content, onChange, mergeFields = [] }: {
  content: string;
  onChange: (html: string) => void;
  mergeFields?: MergeField[];
}) {
  const editor = useEditor({
    extensions: [
      StarterKit, Underline, Highlight,
      Link.configure({ openOnClick: false }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Table.configure({ resizable: true }), TableRow, TableCell, TableHeader,
    ],
    content,
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
  });

  // Keep external content in sync when it changes from outside (e.g. fill-from-case).
  useEffect(() => {
    if (editor && content !== editor.getHTML()) editor.commands.setContent(content, false);
  }, [content]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!editor) return null;
  const btn = (active: boolean) => `p-1.5 rounded-sm ${active ? 'bg-oxblood-wash text-oxblood' : 'text-ink-muted hover:text-ink'}`;

  return (
    <div className="border border-rule rounded-DEFAULT bg-surface">
      <div className="flex flex-wrap items-center gap-0.5 border-b border-rule p-1.5">
        <button onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} className={btn(editor.isActive('heading', { level: 1 }))}><Heading1 size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} className={btn(editor.isActive('heading', { level: 2 }))}><Heading2 size={15} /></button>
        <span className="w-px h-4 bg-rule mx-1" />
        <button onClick={() => editor.chain().focus().toggleBold().run()} className={btn(editor.isActive('bold'))}><Bold size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleItalic().run()} className={btn(editor.isActive('italic'))}><Italic size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleUnderline().run()} className={btn(editor.isActive('underline'))}><U size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleHighlight().run()} className={btn(editor.isActive('highlight'))}><Highlighter size={15} /></button>
        <span className="w-px h-4 bg-rule mx-1" />
        <button onClick={() => editor.chain().focus().toggleBulletList().run()} className={btn(editor.isActive('bulletList'))}><List size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleOrderedList().run()} className={btn(editor.isActive('orderedList'))}><ListOrdered size={15} /></button>
        <span className="w-px h-4 bg-rule mx-1" />
        <button onClick={() => editor.chain().focus().setTextAlign('left').run()} className={btn(editor.isActive({ textAlign: 'left' }))}><AlignLeft size={15} /></button>
        <button onClick={() => editor.chain().focus().setTextAlign('center').run()} className={btn(editor.isActive({ textAlign: 'center' }))}><AlignCenter size={15} /></button>
        <button onClick={() => editor.chain().focus().setTextAlign('right').run()} className={btn(editor.isActive({ textAlign: 'right' }))}><AlignRight size={15} /></button>
        <span className="w-px h-4 bg-rule mx-1" />
        <button onClick={() => { const url = prompt('Link URL'); if (url) editor.chain().focus().setLink({ href: url }).run(); }} className={btn(editor.isActive('link'))}><LinkIcon size={15} /></button>
        <button onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()} className={btn(false)}><TableIcon size={15} /></button>
        {mergeFields.length > 0 && (
          <select onChange={(e) => { if (e.target.value) { editor.chain().focus().insertContent(e.target.value).run(); e.target.value = ''; } }}
            className="ml-2 text-xs border border-rule rounded-sm px-1.5 py-1 text-ink-muted bg-surface">
            <option value="">Insert field…</option>
            {mergeFields.map((f) => <option key={f.token} value={f.token}>{f.label}</option>)}
          </select>
        )}
      </div>
      <EditorContent editor={editor} className="prose prose-sm max-w-none p-5 min-h-[420px] focus:outline-none [&_.ProseMirror]:outline-none [&_.ProseMirror]:min-h-[400px] [&_table]:border-collapse [&_td]:border [&_td]:border-rule [&_td]:p-1 [&_th]:border [&_th]:border-rule [&_th]:p-1 [&_th]:bg-paper-deep" />
    </div>
  );
}
