import { useEffect, useState } from 'react';
import { AvatarOrb, Button, Card, KeyValue, PageHeader, useToast } from '@components/index';
import { hologram, voice } from '@services/api';
import { emotionColors } from '@design/colors';
import type { AvatarState } from '@services/types';

const EMOTIONS = Object.keys(emotionColors);
const GESTURES = ['idle', 'nod', 'shake', 'wave', 'point', 'think', 'shrug', 'lean_in', 'tilt'];

/** Avatar control surface (docs/09-HOLOGRAM.md). */
export function AvatarHome() {
  const [state, setState] = useState<AvatarState | null>(null);
  const [speech, setSpeech] = useState('Hello, I am AERA.');
  const showToast = useToast((s) => s.show);

  const refresh = async () => {
    try {
      setState(await hologram.status());
    } catch {
      /* hologram may be disabled */
    }
  };

  useEffect(() => void refresh(), []);

  const act = async (fn: () => Promise<AvatarState>) => {
    try {
      setState(await fn());
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'action failed', 'error');
    }
  };

  const speak = async () => {
    try {
      const result = await voice.speak(speech);
      showToast(`Spoke with ${result.emotion} emotion`, 'success');
      void refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'speech failed', 'error');
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Hologram"
        subtitle="Avatar emotion, gesture and lip-sync state"
        action={<Button variant="ghost" onClick={() => void refresh()}>Refresh</Button>}
      />

      <div className="flex flex-wrap gap-4">
        <Card className="flex w-[260px] shrink-0 flex-col items-center justify-center py-8">
          <AvatarOrb
            size={64}
            emotion={state?.emotion}
            speaking={state?.speaking}
            showLabel
          />
          <div className="mt-4 flex gap-1.5">
            <Button size="sm" variant="ghost" onClick={() => void act(hologram.show)}>
              Show
            </Button>
            <Button size="sm" variant="ghost" onClick={() => void act(hologram.hide)}>
              Hide
            </Button>
          </div>
        </Card>

        <div className="flex min-w-[280px] flex-1 flex-col gap-3">
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
              <Button variant="primary" onClick={() => void speak()}>Speak</Button>
            </div>
            <p className="mt-2 text-[11px] text-[var(--aera-text-muted)]">
              Emotion is detected from the text and drives the avatar automatically.
            </p>
          </Card>

          {state && (
            <Card title="State">
              <KeyValue label="Visible" value={String(state.visible)} />
              <KeyValue label="Emotion" value={state.emotion} />
              <KeyValue label="Intensity" value={state.intensity.toFixed(2)} />
              <KeyValue label="Gesture" value={state.gesture} />
              <KeyValue label="Speaking" value={String(state.speaking)} />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

export default AvatarHome;
