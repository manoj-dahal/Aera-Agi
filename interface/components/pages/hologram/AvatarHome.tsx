/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Box, RefreshCw, Trash2, Upload } from 'lucide-react';
import {
  Button,
  Card,
  KeyValue,
  LazyAvatarViewer,
  PageHeader,
  ParticleSphere,
  StatusPill,
  Tag,
  useToast,
} from '@components/index';
import { useAvatarStore } from '@store/index';
import { hologram, voice } from '@services/api';
import { detectHost } from '@services/transport';
import { emotionColors } from '@design/colors';
import { cn } from '@utils/cn';
import type { AvatarState } from '@services/types';

const EMOTIONS = Object.keys(emotionColors);
const GESTURES = ['idle', 'nod', 'shake', 'wave', 'point', 'think', 'shrug', 'lean_in', 'tilt'];

/**
 * Hologram: avatar model management and live control (docs/09-HOLOGRAM.md).
 *
 * AERA ships no character of its own. Models are supplied by the user, either
 * dropped into the avatars directory or uploaded here.
 */
export function AvatarHome() {
  const { models, active, loading, uploading, progress, error, load, scan, select, upload,
    importNative, remove, useOrb } =
    useAvatarStore();
  const [state, setState] = useState<AvatarState | null>(null);
  const [speech, setSpeech] = useState('Hello, I am AERA.');
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const showToast = useToast((s) => s.show);

  useEffect(() => {
    void load();
    void hologram.status().then(setState).catch(() => {});
  }, [load]);

  const act = async (fn: () => Promise<AvatarState>) => {
    try {
      setState(await fn());
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'action failed', 'error');
    }
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) return;

    // On the desktop the file already exists on disk, so copy it directly
    // rather than reading a few hundred megabytes through the browser.
    if (detectHost() === 'desktop') {
      const paths = Array.from(files)
        .map((file) => (file as File & { path?: string }).path)
        .filter((path): path is string => Boolean(path));
      if (paths.length === files.length) {
        if (await importNative(paths)) {
          showToast(`Imported ${paths.length} file(s)`, 'success');
        } else {
          showToast(useAvatarStore.getState().error ?? 'import failed', 'error');
        }
        return;
      }
    }

    for (const file of Array.from(files)) {
      const model = await upload(file);
      if (!model) {
        // upload() returns null on failure; the reason is on the store.
        showToast(useAvatarStore.getState().error ?? `could not upload ${file.name}`, 'error');
        continue;
      }
      showToast(`Uploaded ${model.name}`, 'success');
      if (model.warnings.length) {
        showToast(model.warnings[0]!, 'error');
      }
    }
  };

  const speak = async () => {
    try {
      const result = await voice.speak(speech);
      showToast(`Spoke with ${result.emotion} emotion`, 'success');
      void hologram.status().then(setState).catch(() => {});
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'speech failed', 'error');
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Hologram"
        subtitle="Your avatar models, emotion and gesture control"
        action={
          <div className="flex gap-2">
            <Button variant="ghost" icon={<RefreshCw size={13} />} onClick={() => void scan()}>
              Rescan
            </Button>
            <Button
              variant="primary"
              icon={<Upload size={14} />}
              onClick={() => fileInput.current?.click()}
            >
              Upload Model
            </Button>
          </div>
        }
      />

      <input
        ref={fileInput}
        type="file"
        accept=".glb,.gltf,.obj,.mtl,.bin,.fbx,.vrm,.zip,.png,.jpg,.jpeg"
        multiple
        hidden
        onChange={(e) => void handleFiles(e.target.files)}
      />

      <div className="flex flex-wrap gap-4">
        {/* -------- live preview -------- */}
        <Card className="flex w-[340px] shrink-0 flex-col items-center justify-center py-6">
          {active ? (
            <LazyAvatarViewer
              modelId={active.id}
              format={active.format}
              state={state?.speaking ? 'speaking' : 'idle'}
              emotion={state?.emotion}
              size={280}
              onError={(message) => showToast(message, 'error')}
            />
          ) : (
            <ParticleSphere
              state={state?.speaking ? 'speaking' : 'idle'}
              emotion={state?.emotion}
              size={240}
            />
          )}
          <p className="mt-3 text-[11.5px] text-[var(--aera-text-muted)]">
            {active ? active.name : 'Particle orb (no model selected)'}
          </p>
          <div className="mt-3 flex gap-1.5">
            <Button size="sm" variant="ghost" onClick={() => void act(hologram.show)}>
              Show
            </Button>
            <Button size="sm" variant="ghost" onClick={() => void act(hologram.hide)}>
              Hide
            </Button>
            {active && (
              <Button size="sm" variant="subtle" onClick={useOrb}>
                Use orb
              </Button>
            )}
          </div>
        </Card>

        {/* -------- controls -------- */}
        <div className="flex min-w-[300px] flex-1 flex-col gap-3">
          <Card title="Emotion">
            <div className="flex flex-wrap gap-1.5">
              {EMOTIONS.map((emotion) => (
                <button
                  key={emotion}
                  onClick={() => void act(() => hologram.setEmotion(emotion, 0.85))}
                  className="rounded-md px-2.5 py-1 text-[11.5px] transition-transform hover:scale-105"
                  style={{
                    color: emotionColors[emotion as keyof typeof emotionColors],
                    background: `${emotionColors[emotion as keyof typeof emotionColors]}22`,
                  }}
                >
                  {emotion}
                </button>
              ))}
            </div>
          </Card>

          <Card title="Gesture">
            <div className="flex flex-wrap gap-1.5">
              {GESTURES.map((gesture) => (
                <Button
                  key={gesture}
                  size="sm"
                  variant="ghost"
                  onClick={() => void act(() => hologram.gesture(gesture))}
                >
                  {gesture}
                </Button>
              ))}
            </div>
          </Card>

          <Card title="Speak">
            <div className="flex gap-2">
              <input
                value={speech}
                onChange={(e) => setSpeech(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void speak()}
                className="selectable flex-1 rounded-md border border-[var(--aera-line-default)] bg-[var(--aera-bg-raised)] px-3 py-2 text-[12.5px]"
              />
              <Button variant="primary" onClick={() => void speak()}>
                Speak
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* -------- model library -------- */}
      <h3 className="mb-2 mt-5 text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
        Model library
      </h3>

      {uploading && (
        <div className="mb-2 rounded-lg border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-3 py-2">
          <div className="mb-1 flex items-center justify-between text-[11.5px]">
            <span className="text-[var(--aera-text-secondary)]">Uploading {uploading}</span>
            <span className="font-mono text-[var(--aera-text-muted)]">
              {Math.round(progress * 100)}%
            </span>
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-[var(--aera-bg-overlay)]">
            <div
              className="h-full rounded-full bg-[var(--aera-accent-primary)] transition-[width] duration-150"
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
        </div>
      )}

      {error && !uploading && (
        <div className="mb-2 flex items-start gap-1.5 rounded-lg border border-[var(--aera-danger)] px-3 py-2 text-[11.5px] text-[var(--aera-danger)]">
          <AlertTriangle size={12} className="mt-px shrink-0" />
          <span className="selectable">{error}</span>
        </div>
      )}

      <div
        onDragEnter={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          'rounded-xl border border-dashed p-3 transition-colors',
          dragging
            ? 'border-[var(--aera-accent-primary)] bg-[color-mix(in_srgb,var(--aera-accent-primary)_8%,transparent)]'
            : 'border-[var(--aera-line-default)]',
        )}
      >
        {models.length === 0 ? (
          <div className="py-8 text-center">
            <Box size={22} className="mx-auto mb-2 text-[var(--aera-text-disabled)]" />
            <p className="text-[12.5px] text-[var(--aera-text-muted)]">
              {loading ? 'Scanning…' : 'No models yet. Drop a .glb or a .zip here, or upload one.'}
            </p>
            <p className="mt-1 text-[11px] text-[var(--aera-text-disabled)]">
              GLB is recommended. Marketplace .zip downloads are unpacked automatically.
            </p>
          </div>
        ) : (
          <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(250px,1fr))]">
            {models.map((model) => (
              <Card
                key={model.id}
                interactive
                onClick={() => void select(model.id)}
                className={cn(
                  active?.id === model.id && 'border-[var(--aera-accent-primary)]',
                )}
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <h4 className="truncate text-[12.5px] font-semibold">{model.name}</h4>
                  {active?.id === model.id && <StatusPill status="running" label="active" />}
                </div>

                <div className="mb-1.5 flex flex-wrap gap-1">
                  <Tag>{model.format}</Tag>
                  <Tag>{model.kind}</Tag>
                  {model.variant !== 'unspecified' && <Tag>{model.variant}</Tag>}
                  {model.has_skeleton && <Tag>rigged</Tag>}
                  {/* Shape keys are what speech drives; say whether they are
                      usable rather than just present. */}
                  {model.can_lip_sync && <Tag>lip-sync</Tag>}
                  {model.has_morph_targets && !model.can_lip_sync && (
                    <Tag>{model.morph_targets.length} shape keys</Tag>
                  )}
                </div>

                {model.parsed ? (
                  <>
                    <KeyValue label="Triangles" value={(model.triangles ?? 0).toLocaleString()} />
                    <KeyValue label="Size" value={`${model.size_mb} MB`} />
                    {model.dimensions && (
                      <KeyValue
                        label="Dimensions"
                        value={model.dimensions.map((d) => Math.round(d)).join(' × ')}
                      />
                    )}
                    {model.has_morph_targets && (
                      <KeyValue
                        label="Lip-sync"
                        value={
                          model.can_lip_sync
                            ? `${Object.keys(model.viseme_bindings).length}/6 visemes`
                            : 'no matching visemes'
                        }
                      />
                    )}
                  </>
                ) : (
                  <p className="text-[11px] text-[var(--aera-text-muted)]">
                    Catalogued but not parsed.
                  </p>
                )}

                {model.warnings.length > 0 && (
                  <div className="mt-2 flex items-start gap-1.5 text-[10.5px] text-[var(--aera-warning)]">
                    <AlertTriangle size={11} className="mt-px shrink-0" />
                    <span>{model.warnings[0]}</span>
                  </div>
                )}

                <Button
                  size="sm"
                  variant="subtle"
                  icon={<Trash2 size={11} />}
                  className="mt-2 !text-[var(--aera-danger)]"
                  onClick={(e) => {
                    e.stopPropagation();
                    void remove(model.id);
                  }}
                >
                  Remove
                </Button>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default AvatarHome;
