/** AERA service layer: typed client, transport and shared contracts. */

export { api, default as client, agents, avatars, automation, chat, hologram, memory, models, onStreamToken, skills, streamOverHttp, system, voice, workspace } from './api';
export { TransportError, detectHost, nativeBridge, unwrap, whenReady } from './transport';
export type { HostKind } from './transport';
export * from './types';
