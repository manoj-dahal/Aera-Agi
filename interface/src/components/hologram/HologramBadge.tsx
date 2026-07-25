import { emotionColors, type Emotion } from '@design/colors';

/**
 * Small orbital indicator shown above the workspace panel
 * (docs/04-DASHBOARD.md, left column).
 */
export function HologramBadge({
  emotion = 'neutral',
  active = false,
}: {
  emotion?: string;
  active?: boolean;
}) {
  const colour = emotionColors[emotion as Emotion] ?? emotionColors.neutral;

  return (
    <div className="flex flex-col items-center gap-1 py-2">
      <div className="relative flex h-[42px] w-[110px] items-center justify-center">
        {[1, 0.66, 0.36].map((scale, index) => (
          <span
            key={scale}
            className="absolute rounded-[50%] border"
            style={{
              width: 110 * scale,
              height: 34 * scale,
              borderColor: `${colour}${index === 2 ? 'cc' : index === 1 ? '77' : '44'}`,
              animation: active ? `aera-spin ${7 + index * 3}s linear infinite` : undefined,
            }}
          />
        ))}
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{ background: colour, boxShadow: `0 0 10px ${colour}` }}
        />
      </div>
      <span className="text-[9.5px] uppercase tracking-[0.14em] text-[var(--aera-text-muted)]">
        Hologram
      </span>
    </div>
  );
}
