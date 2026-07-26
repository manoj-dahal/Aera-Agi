/** Conversation state and streaming lifecycle. */

import { create } from 'zustand';
import { chat, onStreamToken, streamOverHttp } from '@services/api';
import { detectHost } from '@services/transport';
import type { ChatMessage } from '@services/types';

interface ChatState {
  messages: ChatMessage[];
  conversationId: string;
  streaming: boolean;
  error: string | null;

  send: (text: string) => Promise<void>;
  /** Post a message the model did not generate, e.g. an upload receipt. */
  append: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  clear: () => void;
  newConversation: () => void;
  transcript: () => string;
}

const newId = () => Math.random().toString(36).slice(2, 10);
const newConversationId = () => `ui-${Date.now().toString(36)}`;

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  conversationId: newConversationId(),
  streaming: false,
  error: null,

  send: async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || get().streaming) return;

    const userMessage: ChatMessage = {
      id: newId(),
      role: 'user',
      content: trimmed,
      timestamp: Date.now() / 1000,
    };
    const replyId = newId();
    const reply: ChatMessage = {
      id: replyId,
      role: 'assistant',
      content: '',
      streaming: true,
      timestamp: Date.now() / 1000,
    };

    set((s) => ({
      messages: [...s.messages, userMessage, reply],
      streaming: true,
      error: null,
    }));

    const patch = (changes: Partial<ChatMessage>) =>
      set((s) => ({
        messages: s.messages.map((m) => (m.id === replyId ? { ...m, ...changes } : m)),
      }));

    const finish = (content: string, failed = false) => {
      patch({ content, streaming: false, error: failed });
      set({ streaming: false, error: failed ? content : null });
    };

    const { conversationId } = get();

    if (detectHost() === 'desktop') {
      let buffer = '';
      const dispose = onStreamToken({
        token: (token) => {
          buffer += token;
          patch({ content: buffer });
        },
        done: (full) => {
          finish(full || buffer);
          dispose();
        },
        error: (message) => {
          finish(message, true);
          dispose();
        },
      });

      try {
        await chat.stream(trimmed, conversationId);
      } catch (error) {
        dispose();
        finish(error instanceof Error ? error.message : 'request failed', true);
      }
      return;
    }

    // HTTP host: stream over server-sent events, falling back to a plain POST.
    try {
      let buffer = '';
      await streamOverHttp(trimmed, conversationId, {
        token: (token) => {
          buffer += token;
          patch({ content: buffer });
        },
        done: (full) => finish(full || buffer),
      });
    } catch {
      try {
        const result = await chat.send(trimmed, conversationId);
        patch({ agent: result.agent, provider: result.provider ?? undefined });
        finish(result.output);
      } catch (error) {
        finish(error instanceof Error ? error.message : 'request failed', true);
      }
    }
  },

  append: (message) =>
    set((s) => ({
      messages: [...s.messages, { ...message, id: newId(), timestamp: Date.now() }],
    })),

  clear: () => set({ messages: [], error: null }),

  newConversation: () =>
    set({ messages: [], conversationId: newConversationId(), error: null }),

  transcript: () =>
    get()
      .messages.map((m) => `## ${m.role === 'user' ? 'You' : 'AERA'}\n\n${m.content}\n`)
      .join('\n'),
}));
