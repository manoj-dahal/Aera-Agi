import { create } from 'zustand';
import { useEffect } from 'react';
import { cn } from '@utils/cn';

type ToastKind = 'info' | 'success' | 'error';

interface ToastState {
  message: string | null;
  kind: ToastKind;
  show: (message: string, kind?: ToastKind) => void;
  hide: () => void;
}

export const useToast = create<ToastState>((set) => ({
  message: null,
  kind: 'info',
  show: (message, kind = 'info') => set({ message, kind }),
  hide: () => set({ message: null }),
}));

export function ToastHost() {
  const { message, kind, hide } = useToast();

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(hide, 2600);
    return () => clearTimeout(timer);
  }, [message, hide]);

  return (
    <div
      className={cn(
        'pointer-events-none fixed bottom-5 left-1/2 z-[70] -translate-x-1/2 rounded-lg border px-4 py-2 text-[12.5px] transition-all duration-200',
        message ? 'translate-y-0 opacity-100' : 'translate-y-3 opacity-0',
      )}
      style={{
        background: 'var(--aera-bg-overlay)',
        borderColor:
          kind === 'error'
            ? 'var(--aera-danger)'
            : kind === 'success'
              ? 'var(--aera-success)'
              : 'var(--aera-line-default)',
      }}
      role="status"
      aria-live="polite"
    >
      {message}
    </div>
  );
}
