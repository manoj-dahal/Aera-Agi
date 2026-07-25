import { PlannedFeature } from '@components/widgets/PlannedFeature';

export function PluginHome() {
  return (
    <PlannedFeature
      title="Plugins"
      subtitle="Sandboxed extensions that add agents, tools and UI"
      available={
        <>
          The agent registry already supports registering new agents at runtime, which is
          the extension point plugins will build on. Permission and sandbox primitives
          exist in the security layer.
        </>
      }
      planned={[
        'Plugin manifest loading and lifecycle',
        'Permission prompts and sandbox enforcement',
        'Marketplace browsing and installation',
      ]}
      spec="docs/17-PLUGIN-SYSTEM.md"
    />
  );
}

export default PluginHome;
