/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bot, Cpu, Settings2, Sparkles, Volume2 } from 'lucide-react';
import {
  Button,
  Card,
  ErrorState,
  Field,
  Input,
  KeyValue,
  LoadingState,
  PageHeader,
  Select,
  StatusPill,
  useToast,
} from '@components/index';
import { models, system, voice } from '@services/api';
import { detectHost } from '@services/transport';
import { applyTheme, themes, type ThemeName } from '@design/themes';
import type { ProviderHealth, VoiceLanguages, VoicePersonas } from '@services/types';

type Section = 'ai' | 'voice' | 'system';

const SECTIONS: Array<{ id: Section; label: string; Icon: typeof Bot; hint: string }> = [
  { id: 'ai', label: 'AI', Icon: Bot, hint: 'Models, providers and memory' },
  { id: 'voice', label: 'Voice', Icon: Volume2, hint: 'Speech, emotion and hologram' },
  { id: 'system', label: 'System', Icon: Settings2, hint: 'Appearance, security and status' },
];

const SECRET_OPTIONS = [
  { value: 'openai_api_key', label: 'OpenAI' },
  { value: 'anthropic_api_key', label: 'Anthropic (Claude)' },
  { value: 'gemini_api_key', label: 'Google Gemini' },
  { value: 'openrouter_api_key', label: 'OpenRouter' },
];

/**
 * Settings (docs/13-SETTINGS.md, docs/ui-page/conversation.txt).
 *
 * Exactly three sections — AI, Voice and System — as specified. Advanced
 * options are nested inside them rather than promoted to the top level, and
 * plugin management lives in Apps, not here.
 */
export function SettingsHome() {
  const [section, setSection] = useState<Section | null>(null);
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [providers, setProviders] = useState<Record<string, ProviderHealth>>({});
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [secretName, setSecretName] = useState(SECRET_OPTIONS[0]!.value);
  const [secretValue, setSecretValue] = useState('');
  const [theme, setTheme] = useState<ThemeName>('dark');
  const [languages, setLanguages] = useState<VoiceLanguages | null>(null);
  const [voices, setVoices] = useState<VoicePersonas | null>(null);
  const [newVoiceLabel, setNewVoiceLabel] = useState('');
  const [newVoicePath, setNewVoicePath] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const showToast = useToast((s) => s.show);
  const isDesktop = detectHost() === 'desktop';

  const load = async () => {
    setLoading(true);
    try {
      // These used to be .catch(() => ({})), so an unreachable backend was
      // indistinguishable from a genuinely empty configuration.
      const [settingsData, healthData] = await Promise.all([
        system.settings(),
        models.health(),
      ]);
      setSettings(settingsData as Record<string, unknown>);
      setProviders(healthData as Record<string, ProviderHealth>);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'could not load settings');
    } finally {
      setLoading(false);
    }
    // Secrets are optional: the vault may be locked, which is not an error.
    try {
      const { secrets: stored } = await system.secrets();
      setSecrets(stored);
    } catch {
      setSecrets({});
    }
    // So is the language catalogue: an older backend has no /voice/languages,
    // and the section should degrade to the read-only view rather than break.
    try {
      setLanguages(await voice.languages());
    } catch {
      setLanguages(null);
    }
    try {
      setVoices(await voice.personas());
    } catch {
      setVoices(null);
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

  const changeVoice = async (id: string) => {
    try {
      const persona = await voice.setPersona(id);
      setVoices((current) => (current ? { ...current, active: id } : current));
      showToast(`Voice set to ${persona.label}`, 'success');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'could not switch voice', 'error');
    }
  };

  const addVoice = async () => {
    if (!newVoiceLabel.trim() || !newVoicePath.trim()) {
      return showToast('A name and a model path are both required', 'error');
    }
    try {
      const added = await voice.addVoice({
        label: newVoiceLabel.trim(),
        model_path: newVoicePath.trim(),
      });
      setNewVoiceLabel('');
      setNewVoicePath('');
      showToast(`Added ${added.label}`, 'success');
      void load();
    } catch (error) {
      // The API validates the model and explains what is wrong with it;
      // showing that verbatim is more use than a generic failure.
      showToast(error instanceof Error ? error.message : 'could not add voice', 'error');
    }
  };

  const removeVoice = async (id: string) => {
    try {
      await voice.removeVoice(id);
      showToast('Voice removed', 'success');
      void load();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'could not remove voice', 'error');
    }
  };

  const changeLanguage = async (code: string) => {
    try {
      const result = await voice.setLanguage(code);
      setLanguages((current) => (current ? { ...current, active: code } : current));
      showToast(
        result.supported
          ? `Voice language set to ${result.pack.endonym}`
          : `No pack for "${code}" — falling back to English cues`,
        result.supported ? 'success' : 'error',
      );
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'could not switch language', 'error');
    }
  };

  const changeTheme = (name: ThemeName) => {
    setTheme(name);
    applyTheme(name);
    if (isDesktop) void system.setPreference('theme', name).catch(() => {});
  };

  // --- landing: three buttons only ------------------------------------- //
  if (section === null) {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 p-6">
        <h2 className="mb-3 text-[11px] uppercase tracking-[0.22em] text-[var(--aera-text-muted)]">
          Settings
        </h2>
        {SECTIONS.map(({ id, label, Icon, hint }) => (
          <button
            key={id}
            onClick={() => setSection(id)}
            className="flex w-full max-w-md items-center gap-4 rounded-xl border border-[var(--aera-line-strong)] bg-[var(--aera-bg-surface)] px-5 py-4 text-left transition-colors hover:border-[var(--aera-accent-primary)]"
          >
            <Icon size={20} className="text-[var(--aera-accent-primary)]" strokeWidth={1.7} />
            <span className="flex-1">
              <span className="block text-[15px] font-medium">{label}</span>
              <span className="block text-[11.5px] text-[var(--aera-text-muted)]">{hint}</span>
            </span>
            <span className="text-[var(--aera-text-disabled)]">›</span>
          </button>
        ))}
      </div>
    );
  }

  const back = (
    <Button variant="ghost" size="sm" onClick={() => setSection(null)}>
      ‹ Settings
    </Button>
  );

  const detail = (title: string, data: unknown) => (
    <Card title={title}>
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

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title={SECTIONS.find((s) => s.id === section)!.label}
        subtitle={SECTIONS.find((s) => s.id === section)!.hint}
        action={back}
      />

      {loading && <LoadingState />}
      {error && !loading && <ErrorState message={error} onRetry={() => void load()} />}

      {section === 'ai' && (
        <div className="grid max-w-4xl gap-3 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
          <LocalModelCard providers={providers} />

          <Card title="Providers">
            {Object.entries(providers)
              .filter(([, info]) => !info.local)
              .map(([name, info]) => (
                <div key={name} className="flex items-center justify-between py-1 text-[12px]">
                  <span className="text-[var(--aera-text-muted)]">{name}</span>
                  <StatusPill status={info.healthy ? 'healthy' : 'offline'} />
                </div>
              ))}
          </Card>

          {detail('Model routing', settings.models)}
          {detail('Memory', settings.memory)}

          <Card title="API keys">
            <p className="mb-2.5 text-[11px] text-[var(--aera-text-muted)]">
              Encrypted on this machine, sent only to the provider you choose. AERA runs
              offline without them.
            </p>
            {isDesktop ? (
              <div className="flex flex-col gap-2">
                <Select value={secretName} onChange={(e) => setSecretName(e.target.value)}>
                  {SECRET_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
                <Input
                  type="password"
                  value={secretValue}
                  placeholder="Paste the API key…"
                  onChange={(e) => setSecretValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && void saveSecret()}
                />
                <Button variant="primary" size="sm" onClick={() => void saveSecret()}>
                  Save
                </Button>
              </div>
            ) : (
              <p className="text-[11px] text-[var(--aera-text-disabled)]">
                Keys can only be written from the desktop application. On a server, set
                OPENAI_API_KEY, ANTHROPIC_API_KEY or GEMINI_API_KEY in the environment.
              </p>
            )}
            {Object.entries(secrets).map(([name, masked]) => (
              <KeyValue key={name} label={name} value={<span className="font-mono">{masked}</span>} />
            ))}
          </Card>

          <NestedLink to="/memory" Icon={Sparkles} label="Memory graph" hint="Browse and search recall" />
          <NestedLink to="/agents" Icon={Bot} label="Agents" hint="Roster and lifecycle" />
          <NestedLink to="/models" Icon={Cpu} label="Model manager" hint="Local, cloud and custom" />
        </div>
      )}

      {section === 'voice' && (
        <div className="grid max-w-4xl gap-3 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
          {voices && (
            <Card title="Voice">
              <Field label="Speaking voice">
                <Select
                  value={voices.active ?? voices.builtin[0]}
                  onChange={(e) => void changeVoice(e.target.value)}
                >
                  {voices.personas.map((persona) => (
                    <option
                      key={persona.id}
                      value={persona.id}
                      disabled={persona.custom && persona.available === false}
                    >
                      {persona.label}
                      {persona.custom && persona.available === false ? ' — model missing' : ''}
                    </option>
                  ))}
                </Select>
              </Field>

              {/* Stated rather than discovered from the audio: the two
                  bundled voices carry pitch and timing but do not speak
                  words. A registered model does. */}
              <KeyValue
                label="speech"
                value={
                  <span className="font-mono text-[11px]">
                    {voices.synthesises_speech
                      ? 'articulates words'
                      : 'pitch and timing only — add a model for speech'}
                  </span>
                }
              />

              {voices.custom.map((id) => (
                <div key={id} className="flex items-center justify-between gap-2 pt-1">
                  <span className="font-mono text-[11px] text-[var(--aera-muted)]">{id}</span>
                  <Button variant="ghost" onClick={() => void removeVoice(id)}>
                    Remove
                  </Button>
                </div>
              ))}

              <Field label="Add a voice (Piper .onnx model)">
                <Input
                  placeholder="Name, e.g. Narrator"
                  value={newVoiceLabel}
                  onChange={(e) => setNewVoiceLabel(e.target.value)}
                />
              </Field>
              <Field label="Model path">
                <Input
                  placeholder="~/voices/en_US-amy-medium.onnx"
                  value={newVoicePath}
                  onChange={(e) => setNewVoicePath(e.target.value)}
                />
              </Field>
              <Button onClick={() => void addVoice()}>Add voice</Button>
            </Card>
          )}

          {languages && (
            <Card title={`Language (${languages.count})`}>
              <Field label="Spoken language">
                <Select
                  value={languages.active}
                  onChange={(e) => void changeLanguage(e.target.value)}
                >
                  {languages.languages.map((entry) => (
                    <option key={entry.code} value={entry.code}>
                      {entry.endonym === entry.label
                        ? entry.label
                        : `${entry.endonym} — ${entry.label}`}
                    </option>
                  ))}
                </Select>
              </Field>
              <KeyValue
                label="emotion cues"
                value={<span className="font-mono text-[11px]">{languages.active_pack.emotion_cues}</span>}
              />
              <KeyValue
                label="script"
                value={
                  <span className="font-mono text-[11px]">
                    {languages.active_pack.script}
                    {languages.active_pack.rtl ? ' (right to left)' : ''}
                  </span>
                }
              />
              {/* Stated rather than left to be discovered: Japanese, Korean
                  and ten Indic packs keep numerals, because their readings
                  depend on a counter or on irregular forms not carried here. */}
              <KeyValue
                label="numbers"
                value={
                  <span className="font-mono text-[11px]">
                    {languages.active_pack.spells_all_numbers
                      ? 'spoken as words'
                      : 'read as digits'}
                  </span>
                }
              />
            </Card>
          )}
          {detail('Voice', settings.voice)}
          <NestedLink to="/hologram" Icon={Sparkles} label="Hologram" hint="Avatar emotion and gestures" />
        </div>
      )}

      {section === 'system' && (
        <div className="grid max-w-4xl gap-3 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
          <Card title="Appearance">
            <Field label="Theme">
              <Select value={theme} onChange={(e) => changeTheme(e.target.value as ThemeName)}>
                {Object.values(themes).map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.label}
                  </option>
                ))}
              </Select>
            </Field>
          </Card>
          {detail('Interface', settings.settings)}
          <NestedLink to="/security" Icon={Settings2} label="Security" hint="Permissions and audit" />
          <NestedLink to="/system" Icon={Cpu} label="System status" hint="Runtime and resources" />
          <NestedLink to="/automation" Icon={Settings2} label="Automation" hint="Workflows and runs" />
          <NestedLink to="/workspace" Icon={Settings2} label="Workspace" hint="Project explorer" />
        </div>
      )}
    </div>
  );
}

/** Link out to a nested detail page. */
function NestedLink({
  to,
  label,
  hint,
  Icon,
}: {
  to: string;
  label: string;
  hint: string;
  Icon: typeof Bot;
}) {
  return (
    <Link to={to}>
      <Card interactive>
        <div className="flex items-center gap-3">
          <Icon size={16} className="text-[var(--aera-accent-primary)]" strokeWidth={1.7} />
          <span className="flex-1">
            <span className="block text-[13px] font-medium">{label}</span>
            <span className="block text-[11px] text-[var(--aera-text-muted)]">{hint}</span>
          </span>
          <span className="text-[var(--aera-text-disabled)]">›</span>
        </div>
      </Card>
    </Link>
  );
}

/**
 * Local model status.
 *
 * Per the conversation: when no local runtime is detected there must be no
 * connect button at all — only an offline status line.
 */
function LocalModelCard({ providers }: { providers: Record<string, ProviderHealth> }) {
  const local = Object.entries(providers).filter(
    ([name, info]) => info.local && name !== 'builtin',
  );
  const connected = local.filter(([, info]) => info.healthy);

  return (
    <Card title="Local models">
      {connected.length > 0 ? (
        connected.map(([name]) => (
          <div key={name} className="flex items-center justify-between py-1 text-[12px]">
            <span className="text-[var(--aera-text-muted)]">{name}</span>
            <span className="flex items-center gap-1.5 text-[var(--aera-success)]">
              <i
                className="h-1.5 w-1.5 rounded-full bg-[var(--aera-success)]"
                style={{ boxShadow: '0 0 6px var(--aera-success)' }}
              />
              Connected
            </span>
          </div>
        ))
      ) : (
        <>
          <p className="text-[12px] text-[var(--aera-text-muted)]">Not connected</p>
          <p className="mt-1 text-[11px] text-[var(--aera-text-disabled)]">
            Start a supported local AI service to enable local inference. AERA continues
            to run on the built-in reasoner.
          </p>
        </>
      )}
    </Card>
  );
}

export default SettingsHome;
