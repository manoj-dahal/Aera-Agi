import { cn } from '@utils/cn';

export interface TapToSpeakProps {
  listening?: boolean;
  /** Tap-to-memory is recalling context before listening starts. */
  priming?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

/**
 * Primary interaction control (docs/04-DASHBOARD.md).
 *
 * Tap → voice activation → memory recall → intent detection → response.
 */
export function TapToSpeak({
  listening = false,
  priming = false,
  disabled = false,
  onClick,
}: TapToSpeakProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'relative rounded-full border px-9 py-2.5 text-[14px] font-medium uppercase tracking-[0.14em] transition-all duration-200',
        listening
          ? 'border-[var(--aera-accent-secondary)] text-[var(--aera-accent-secondary)]'
          : 'border-[var(--aera-accent-primary)] text-[var(--aera-accent-primary)] hover:bg-[color-mix(in_srgb,var(--aera-accent-primary)_12%,transparent)]',
        (disabled || priming) && 'opacity-60',
      )}
      style={{
        boxShadow: listening
          ? '0 0 26px color-mix(in srgb, var(--aera-accent-secondary) 45%, transparent)'
          : '0 0 16px color-mix(in srgb, var(--aera-accent-primary) 22%, transparent)',
      }}
    >
      {listening && (
        <span className="absolute inset-0 animate-ping rounded-full border border-[var(--aera-accent-secondary)] opacity-40" />
      )}
      {priming ? 'Recalling…' : listening ? 'Listening…' : 'Tap to Speak'}
    </button>
  );
}
