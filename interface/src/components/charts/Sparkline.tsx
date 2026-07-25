/** Dependency-free sparkline for compact metric trends. */
export interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export function Sparkline({
  data,
  width = 120,
  height = 32,
  color = 'var(--aera-accent-primary)',
}: SparklineProps) {
  if (data.length < 2) {
    return <svg width={width} height={height} aria-hidden />;
  }

  const max = Math.max(...data);
  const min = Math.min(...data);
  const span = max - min || 1;
  const step = width / (data.length - 1);

  const points = data
    .map((value, i) => `${i * step},${height - ((value - min) / span) * height}`)
    .join(' ');

  return (
    <svg width={width} height={height} role="img" aria-label="trend">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
