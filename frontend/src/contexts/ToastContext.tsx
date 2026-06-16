import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Check, AlertTriangle, X } from 'lucide-react';

type ToastType = 'success' | 'error';

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message: string, type: ToastType = 'success') => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => dismiss(id), 2500);
  }, [dismiss]);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast stack — fixed, bottom-right, above modals */}
      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto flex items-center gap-2.5 bg-surface border border-rule
                       rounded-DEFAULT shadow-modal pl-3 pr-2 py-2.5 min-w-[240px] max-w-sm animate-fade-up"
          >
            <span className={t.type === 'success' ? 'text-oxblood' : 'text-oxblood'}>
              {t.type === 'success'
                ? <Check size={15} strokeWidth={2} />
                : <AlertTriangle size={15} strokeWidth={2} />}
            </span>
            <span className="flex-1 text-sm text-ink">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="text-ink-faint hover:text-ink-muted transition-colors"
              aria-label="Dismiss"
            >
              <X size={14} strokeWidth={1.5} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}
