import { PlannedFeature } from '@components/widgets/PlannedFeature';

export function AppsHome() {
  return (
    <PlannedFeature
      title="Apps"
      subtitle="Desktop application integration through the Memory Graph"
      available={
        <>
          The Git Agent inspects repositories today, and the Terminal Agent can drive
          command-line tools once enabled. Both share context through the memory graph,
          which is the integration substrate the Apps system builds on.
        </>
      }
      planned={[
        'Application discovery and launcher',
        'VS Code, Blender, Photoshop, Premiere and DaVinci connectors',
        'Custom application manager and per-app automation',
      ]}
      spec="docs/10-APPS.md, docs/apps/"
    />
  );
}

export default AppsHome;
