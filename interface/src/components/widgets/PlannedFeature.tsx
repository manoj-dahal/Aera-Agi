import type { ReactNode } from 'react';
import { PageHeader } from './SectionTitle';
import { Card } from '@components/cards/Card';

export interface PlannedFeatureProps {
  title: string;
  subtitle: string;
  /** What the backend already provides today. */
  available?: ReactNode;
  /** What still needs building for this screen. */
  planned: string[];
  /** Spec document describing the feature. */
  spec?: string;
}

/**
 * Placeholder for screens whose backend exists only in part.
 *
 * Rendering an honest status beats shipping a screen that looks functional but
 * is wired to nothing.
 */
export function PlannedFeature({
  title,
  subtitle,
  available,
  planned,
  spec,
}: PlannedFeatureProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader title={title} subtitle={subtitle} />

      <div className="flex max-w-2xl flex-col gap-3">
        {available && (
          <Card title="Available now">
            <div className="text-[12.5px] leading-relaxed text-[var(--aera-text-secondary)]">
              {available}
            </div>
          </Card>
        )}

        <Card title="Not implemented yet">
          <ul className="ml-4 list-disc text-[12.5px] leading-relaxed text-[var(--aera-text-muted)]">
            {planned.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {spec && (
            <p className="mt-2.5 font-mono text-[11px] text-[var(--aera-text-disabled)]">
              Specification: {spec}
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
