import { useRef, type KeyboardEvent } from 'react';
import { Button } from '@components/buttons/Button';

export interface ComposerProps {
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
}

export function Composer({ value, disabled, onChange, onSend }: ComposerProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  const autosize = (element: HTMLTextAreaElement) => {
    element.style.height = 'auto';
    element.style.height = `${Math.min(element.scrollHeight, 170)}px`;
  };

  return (
    <div className="flex gap-2 border-t border-[var(--aera-line-default)] bg-[var(--aera-bg-raised)] px-6 py-3.5">
      <textarea
        ref={ref}
        rows={1}
        value={value}
        placeholder="Message AERA…   Enter to send · Shift+Enter for a newline"
        className="selectable max-h-[170px] flex-1 resize-none rounded-[9px] border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-3.5 py-2.5 text-[13.5px] placeholder:text-[var(--aera-text-disabled)] focus:border-[var(--aera-accent-primary)]"
        onChange={(e) => {
          onChange(e.target.value);
          autosize(e.target);
        }}
        onKeyDown={handleKeyDown}
      />
      <Button
        variant="primary"
        onClick={onSend}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className="w-11 !px-0 text-[16px]"
      >
        ↑
      </Button>
    </div>
  );
}
