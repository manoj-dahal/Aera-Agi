import { PlannedFeature } from '@components/widgets/PlannedFeature';

export function TerminalHome() {
  return (
    <PlannedFeature
      title="Terminal"
      subtitle="Allowlisted shell execution through the Terminal Agent"
      available={
        <>
          The Terminal Agent is implemented and enforces a strict allowlist, but it is
          disabled by default. Enable <code>security.allow_terminal</code> in
          <code> config/security.yaml</code>, then invoke it through the Agents page or
          <code> POST /api/v1/agents/task</code>.
        </>
      }
      planned={[
        'Interactive PTY session with streaming output',
        'Command history and replay',
        'Per-command approval prompts in the UI',
      ]}
      spec="docs/15-TERMINAL.md, docs/agents/Terminal-Agent.md"
    />
  );
}

export default TerminalHome;
