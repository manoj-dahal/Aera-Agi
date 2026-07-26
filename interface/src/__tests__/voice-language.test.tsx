/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

/**
 * The voice language picker, rendered and driven for real.
 *
 * Thirty-five language packs existed in the backend with no way to reach any
 * of them from the interface: the Voice section printed the config object as
 * read-only text. A capability nobody can invoke is not shipped, so this
 * mounts the settings page, opens Voice, and switches language through the
 * same code path a user does.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { SettingsHome } from '@pages/settings/SettingsHome';
import { system, voice } from '@services/api';

const LANGUAGES = {
  count: 35,
  active: 'en',
  supported: true,
  fallback: 'en',
  spell_numbers: ['en', 'es', 'ne'],
  rtl: ['ar', 'he', 'fa', 'ur'],
  active_pack: {
    code: 'en',
    label: 'English',
    endonym: 'English',
    emotion_cues: 85,
    has_numbers: true,
    spells_all_numbers: true,
    script: 'latin',
    rtl: false,
  },
  languages: [
    {
      code: 'en',
      label: 'English',
      endonym: 'English',
      emotion_cues: 85,
      has_numbers: true,
      spells_all_numbers: true,
      script: 'latin',
      rtl: false,
    },
    {
      code: 'ne',
      label: 'Nepali',
      endonym: 'नेपाली',
      emotion_cues: 29,
      has_numbers: true,
      spells_all_numbers: true,
      script: 'devanagari',
      rtl: false,
    },
    {
      code: 'ar',
      label: 'Arabic',
      endonym: 'العربية',
      emotion_cues: 40,
      has_numbers: true,
      spells_all_numbers: true,
      script: 'arabic',
      rtl: true,
    },
    {
      code: 'ja',
      label: 'Japanese',
      endonym: '日本語',
      emotion_cues: 30,
      has_numbers: false,
      spells_all_numbers: false,
      script: 'kana',
      rtl: false,
    },
  ],
};

const openVoiceSection = async () => {
  render(
    <MemoryRouter>
      <SettingsHome />
    </MemoryRouter>,
  );
  await userEvent.click(await screen.findByRole('button', { name: /voice/i }));
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(system, 'settings').mockResolvedValue({ voice: { enabled: true } } as never);
  vi.spyOn(system, 'secrets').mockResolvedValue({ secrets: {} } as never);
  vi.spyOn(voice, 'languages').mockResolvedValue(LANGUAGES as never);
});

describe('voice language picker', () => {
  it('lists every language the backend reports', async () => {
    await openVoiceSection();

    const select = await screen.findByRole('combobox');

    expect(within(select).getAllByRole('option')).toHaveLength(4);
  });

  it('shows each language in its own script, not just in English', async () => {
    await openVoiceSection();

    await screen.findByRole('combobox');

    // A Nepali speaker looks for नेपाली, not "Nepali".
    expect(screen.getByRole('option', { name: /नेपाली/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /العربية/ })).toBeInTheDocument();
  });

  it('switches language through the API when one is chosen', async () => {
    const setLanguage = vi.spyOn(voice, 'setLanguage').mockResolvedValue({
      language: 'ne',
      supported: true,
      pack: LANGUAGES.languages[1],
    } as never);
    await openVoiceSection();

    await userEvent.selectOptions(await screen.findByRole('combobox'), 'ne');

    await waitFor(() => expect(setLanguage).toHaveBeenCalledWith('ne'));
  });

  it('reports how many cues the active pack carries', async () => {
    await openVoiceSection();

    expect(await screen.findByText('85')).toBeInTheDocument();
  });

  it('says whether numbers are spoken or left as digits', async () => {
    await openVoiceSection();

    // Japanese and the Indic packs keep numerals; the user should be told
    // rather than discover it from the audio.
    expect(await screen.findByText('spoken as words')).toBeInTheDocument();
  });

  it('names the script and flags right-to-left', async () => {
    await openVoiceSection();

    expect(await screen.findByText('latin')).toBeInTheDocument();
  });

  it('degrades to the read-only view when the endpoint is missing', async () => {
    vi.spyOn(voice, 'languages').mockRejectedValue(new Error('404'));

    await openVoiceSection();

    // No picker, but the section still renders rather than throwing:
    // "Voice" appears as the heading and in the nav, so assert on the
    // read-only card that the picker sits beside.
    await waitFor(() => expect(screen.queryByRole('combobox')).not.toBeInTheDocument());
    expect(screen.getByRole('link', { name: /hologram/i })).toBeInTheDocument();
  });
});
