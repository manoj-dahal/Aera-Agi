import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Button, Card, CardGrid, Field, Input, KeyValue, PageHeader,
  Select, StatusPill, useToast,
} from '@components/index';
import { models, system } from '@services/api';
import { detectHost } from '@services/transport';
import { applyTheme, themes, type ThemeName } from '@design/themes';
import type { ProviderHealth } from '@services/types';

const SECRET_OPTIONS = [
  { value: 'openai_api_key', label: 'OpenAI' },
  { value: 'anthropic_api_key', label: 'Anthropic (Claude)' },
  { value: 'gemini_api_key', label: 'Google Gemini' },
  { value: 'openrouter_api_key', label: 'OpenRouter' },
];

/** Settings: AI, appearance and encrypted credentials (docs/13-SETTINGS.md). */
export function SettingsHome() {
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [providers, setProviders] = useState<Record<string, ProviderHealth>>({});
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [secretName, setSecretName] = useState(SECRET_OPTIONS[0]!.value);
  const [secretValue, setSecretValue] = useState('');
  const [theme, setTheme] = useState<ThemeName>('dark');
  const showToast = useToast((s) => s.show);
  const isDesktop = detectHost() === 'desktop';

  const load = async () => {
    const [settingsData, healthData] = await Promise.all([
      system.settings().catch(() => ({})),
      models.health().catch(() => ({})),
    ]);
    setSettings(settingsData as Record<string, unknown>);
    setProviders(healthData as Record<string, ProviderHealth>);
    try {
      const { secrets: stored } = await system.secrets();
      setSecrets(stored);
    } catch {
      setSecrets({});
    }
  };

  useEffect(() => void load(), []);

  const saveSecret = async () => {
    if (!secretValue.trim()) return showToast('Enter a key first', 'error');
    try {
      await system.setSecret(secretName, secretValue.trim());
      setSecretValue('');
      showToast('Saved to the encrypted vault', 'success');
      void load();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'could not save', 'error');
    }
  };

  const changeTheme = (name: ThemeName) => {
    setTheme(name);
    applyTheme(name);
    if (isDesktop) void system.setPreference('theme', name).catch(() => {});
  };

  const section = (title: string, data: unknown) => (
    <Card title={title} key={title}>
      {Object.entries((data ?? {}) as Record<string, unknown>).map(([key, value]) => (
        <KeyValue
          key={key}
          label={key}
          value={
            <span className="font-mono text-[11px]">
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </span>
          }
        />
      ))}
    </Card>
  );

  // The spec keeps the top bar to six destinations, so the detailed
  // subsystem pages are reached from here (docs/13-SETTINGS.md).
  const SUBSYSTEMS = [
    ['/memory', 'Memory', 'Browse and search the knowledge graph'],
    ['/agents', 'Agents', 'Roster, status and lifecycle control'],
    ['/workspace', 'Workspace', 'Project explorer and file search'],
    ['/models', 'Models', 'Local and cloud providers'],
    ['/automation', 'Automation', 'Workflows and run history'],
    ['/hologram', 'Hologram', 'Avatar emotion and gestures'],
    ['/security', 'Security', 'Permissions and the audit trail'],
    ['/system', 'System', 'Runtime and resource status'],
    ['/terminal', 'Terminal', 'Allowlisted shell execution'],
    ['/docker', 'Docker', 'Container management'],
    ['/plugins', 'Plugins', 'Sandboxed extensions'],
  ] as const;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader title="Settings" subtitle="AI, appearance and credentials" />

      <h3 className="mb-2 text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
        Subsystems
      </h3>
      <CardGrid className="mb-5">
        {SUBSYSTEMS.map(([to, label, description]) => (
          <Link key={to} to={to}>
            <Card interactive title={label}>
              <p className="text-[11.5px] text-[var(--aera-text-muted)]">{description}</p>
            </Card>
          </Link>
        ))}
      </CardGrid>

      <Card title="Appearance" className="mb-4 max-w-sm">
        <Field label="Theme">
          <Select value={theme} onChange={(e) => changeTheme(e.target.value as ThemeName)}>
            {Object.values(themes).map((t) => (
              <option key={t.name} value={t.name}>{t.label}</option>
            ))}
          </Select>
        </Field>
      </Card>

      <CardGrid className="mb-5">
        {section('Interface', settings.settings)}
        {section('Models', settings.models)}
        {section('Memory', settings.memory)}
        {section('Voice', settings.voice)}
        <Card title="Providers">
          {Object.entries(providers).map(([name, info]) => (
            <div key={name} className="flex items-center justify-between py-0.5 text-[12px]">
              <span className="text-[var(--aera-text-muted)]">{name}</span>
              <StatusPill status={info.healthy ? 'healthy' : 'offline'} />
            </div>
          ))}
        </Card>
      </CardGrid>

      <h3 className="mb-1.5 text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
        API keys
      </h3>
      <p className="mb-2.5 text-[11.5px] text-[var(--aera-text-muted)]">
        Encrypted at rest on this machine and sent only to the provider you choose.
        AERA runs fully offline without them.
      </p>

      {isDesktop ? (
        <div className="mb-3 flex flex-wrap gap-2">
          <Select
            value={secretName}
            onChange={(e) => setSecretName(e.target.value)}
            className="!w-52"
          >
            {SECRET_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </Select>
          <Input
            type="password"
            value={secretValue}
            placeholder="Paste the API key…"
            onChange={(e) => setSecretValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void saveSecret()}
            className="max-w-md"
          />
          <Button variant="primary" onClick={() => void saveSecret()}>Save</Button>
        </div>
      ) : (
        <p className="mb-3 text-[11.5px] text-[var(--aera-text-disabled)]">
          Keys can only be written from the desktop application. On a server, set
          OPENAI_API_KEY, ANTHROPIC_API_KEY or GEMINI_API_KEY in the environment.
        </p>
      )}

      <CardGrid>
        {Object.entries(secrets).length === 0 ? (
          <p className="text-[12.5px] text-[var(--aera-text-muted)]">No API keys stored.</p>
        ) : (
          Object.entries(secrets).map(([name, masked]) => (
            <Card key={name} title={name}>
              <p className="font-mono text-[11px] text-[var(--aera-text-muted)]">{masked}</p>
            </Card>
          ))
        )}
      </CardGrid>
    </div>
  );
}

export default SettingsHome;
