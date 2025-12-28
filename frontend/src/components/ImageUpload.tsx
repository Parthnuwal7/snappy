import { useState, useRef, useEffect } from 'react';
import { api } from '../api';

interface ImageUploadProps {
    type: 'logo' | 'signature' | 'qr';
    label: string;
    description?: string;
    onUploadComplete?: (path: string) => void;
    onError?: (error: string) => void;
    className?: string;
}

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

    // Load existing image on mount
    useEffect(() => {
        loadExistingImage();
    }, [type]);

    const loadExistingImage = async () => {
        try {
            const result = await api.getSignedUrl(type);
            if (result.signed_url) {
                setPreviewUrl(result.signed_url);
            }
        } catch {
            // No existing image, that's fine
        }
    };

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Validate file type
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
        if (!validTypes.includes(file.type)) {
            const errMsg = 'Please select a JPG or PNG image';
            setError(errMsg);
            onError?.(errMsg);
            return;
        }

        // Validate file size (5MB max)
        const maxSize = 5 * 1024 * 1024;
        if (file.size > maxSize) {
            const errMsg = 'Image must be less than 5MB';
            setError(errMsg);
            onError?.(errMsg);
            return;
        }

        setError(null);
        setIsUploading(true);

        try {
            // Show local preview immediately
            const localPreview = URL.createObjectURL(file);
            setPreviewUrl(localPreview);

            // Upload to server
            const result = await api.uploadImage(type, file);

            // Get signed URL for the uploaded image
            const signedResult = await api.getSignedUrl(type);
            if (signedResult.signed_url) {
                setPreviewUrl(signedResult.signed_url);
            }

            onUploadComplete?.(result.path);
        } catch (err: any) {
            const errMsg = err.message || 'Upload failed';
            setError(errMsg);
            onError?.(errMsg);
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
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        } catch (err: any) {
            setError(err.message || 'Delete failed');
        } finally {
            setIsUploading(false);
        }
    };

    const triggerFileSelect = () => {
        fileInputRef.current?.click();
    };

    const getPlaceholderIcon = () => {
        switch (type) {
            case 'logo':
                return (
                    <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                );
            case 'signature':
                return (
                    <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                );
            case 'qr':
                return (
                    <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
                    </svg>
                );
        }
    };

    return (
        <div className={`${className}`}>
            <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
            {description && <p className="text-xs text-gray-500 mb-2">{description}</p>}

            <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/jpg,image/png"
                onChange={handleFileSelect}
                className="hidden"
            />

            <div className="flex items-start gap-4">
                {/* Preview / Placeholder */}
                <div
                    onClick={triggerFileSelect}
                    className={`
            relative w-32 h-32 border-2 border-dashed rounded-lg cursor-pointer
            flex items-center justify-center overflow-hidden
            ${previewUrl ? 'border-indigo-300 bg-indigo-50' : 'border-gray-300 bg-gray-50'}
            hover:border-indigo-500 hover:bg-indigo-50 transition-colors
            ${isUploading ? 'opacity-50 pointer-events-none' : ''}
          `}
                >
                    {isUploading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-white/80">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
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
                        <div className="text-center">
                            {getPlaceholderIcon()}
                            <p className="mt-1 text-xs text-gray-500">Click to upload</p>
                        </div>
                    )}
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2">
                    <button
                        type="button"
                        onClick={triggerFileSelect}
                        disabled={isUploading}
                        className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                    >
                        {previewUrl ? 'Change' : 'Upload'}
                    </button>

                    {previewUrl && (
                        <button
                            type="button"
                            onClick={handleDelete}
                            disabled={isUploading}
                            className="px-3 py-1.5 text-sm text-red-600 border border-red-300 rounded hover:bg-red-50 disabled:opacity-50"
                        >
                            Remove
                        </button>
                    )}
                </div>
            </div>

            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        </div>
    );
}
