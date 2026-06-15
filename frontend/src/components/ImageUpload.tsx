import { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import { Image as ImageIcon, PenLine, QrCode, Upload, Trash2 } from 'lucide-react';

interface ImageUploadProps {
  type: 'logo' | 'signature' | 'qr';
  label: string;
  description?: string;
  onUploadComplete?: (path: string) => void;
  onError?: (error: string) => void;
  className?: string;
}

const PLACEHOLDER_ICON = {
  logo: ImageIcon,
  signature: PenLine,
  qr: QrCode,
} as const;

export default function ImageUpload({
  type,
  label,
  description,
  onUploadComplete,
  onError,
  className = '',
}: ImageUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    api.getSignedUrl(type)
      .then((res) => { if (!cancelled && res.signed_url) setPreviewUrl(res.signed_url); })
      .catch(() => { /* no existing image, fine */ });
    return () => { cancelled = true; };
  }, [type]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!validTypes.includes(file.type)) {
      const msg = 'Please select a JPG or PNG image.';
      setError(msg); onError?.(msg); return;
    }
    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      const msg = 'Image must be less than 5MB.';
      setError(msg); onError?.(msg); return;
    }

    setError(null);
    setIsUploading(true);
    try {
      setPreviewUrl(URL.createObjectURL(file));
      const result = await api.uploadImage(type, file);
      const signed = await api.getSignedUrl(type);
      if (signed.signed_url) setPreviewUrl(signed.signed_url);
      onUploadComplete?.(result.path);
    } catch (err: any) {
      const msg = err.message || 'Upload failed';
      setError(msg); onError?.(msg);
      setPreviewUrl(null);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!previewUrl) return;
    setIsUploading(true);
    try {
      await api.deleteImage(type);
      setPreviewUrl(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err: any) {
      setError(err.message || 'Delete failed');
    } finally {
      setIsUploading(false);
    }
  };

  const Placeholder = PLACEHOLDER_ICON[type];

  return (
    <div className={className}>
      <div className="field-label">{label}</div>
      {description && <p className="text-xs text-ink-muted mb-3">{description}</p>}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/jpg,image/png"
        onChange={handleFileSelect}
        className="hidden"
      />

      <div className="flex items-start gap-4">
        {/* Preview / drop target */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className={`
            relative w-32 h-32 border border-dashed rounded-DEFAULT overflow-hidden
            flex items-center justify-center transition-colors
            ${previewUrl
              ? 'border-rule-strong bg-surface hover:border-oxblood'
              : 'border-rule-strong bg-paper-deep hover:border-ink hover:bg-surface'}
            ${isUploading ? 'opacity-60' : ''}
          `}
        >
          {isUploading && (
            <div className="absolute inset-0 flex items-center justify-center bg-surface/80">
              <div className="spinner" />
            </div>
          )}

          {previewUrl ? (
            <img
              src={previewUrl}
              alt={label}
              className="w-full h-full object-contain"
              onError={() => setPreviewUrl(null)}
            />
          ) : (
            <div className="text-center px-3">
              <Placeholder size={22} strokeWidth={1.25} className="mx-auto text-ink-faint mb-2" />
              <div className="text-2xs uppercase tracking-eyebrow text-ink-muted">Click to upload</div>
            </div>
          )}
        </button>

        {/* Actions */}
        <div className="flex flex-col gap-2 pt-1">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="btn-secondary !px-3 !py-1.5 text-xs"
          >
            <Upload size={12} strokeWidth={2} />
            <span>{previewUrl ? 'Replace' : 'Upload'}</span>
          </button>

          {previewUrl && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={isUploading}
              className="inline-flex items-center justify-center gap-2 px-3 py-1.5 text-xs
                         text-oxblood hover:text-oxblood-deep hover:bg-oxblood-wash
                         border border-oxblood/30 hover:border-oxblood/60
                         rounded-DEFAULT transition-colors disabled:opacity-50"
            >
              <Trash2 size={12} strokeWidth={2} />
              <span>Remove</span>
            </button>
          )}
        </div>
      </div>

      {error && <p className="field-error">{error}</p>}
    </div>
  );
}
