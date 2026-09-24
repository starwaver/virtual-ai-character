import type { GameState } from './game'

import {
  GAME_VERSION,
  validateGameState,
} from './game'

export const SAVE_NAMESPACE = 'goblin-mercenary'
export const SAVE_VERSION = GAME_VERSION
export const SAVE_KEY = `${SAVE_NAMESPACE}:save:v${SAVE_VERSION}`

export interface SaveStorage {
  getItem: (key: string) => string | null
  setItem: (key: string, value: string) => void
  removeItem: (key: string) => void
}

interface SaveEnvelope {
  namespace: typeof SAVE_NAMESPACE
  version: typeof SAVE_VERSION
  state: GameState
}

export type SaveIssueCode
  = | 'MALFORMED_JSON'
    | 'INVALID_ENVELOPE'
    | 'UNSUPPORTED_VERSION'
    | 'INVALID_STATE'
    | 'STORAGE_READ_FAILED'
    | 'STORAGE_WRITE_FAILED'
    | 'STORAGE_REMOVE_FAILED'

export type SaveLoadResult
  = | { status: 'empty' }
    | { status: 'loaded', state: GameState }
    | { status: 'invalid', issue: SaveIssueCode, path?: string }
    | { status: 'storage-error', issue: SaveIssueCode }

export type SaveWriteResult
  = | { status: 'saved' }
    | { status: 'invalid', issue: SaveIssueCode, path?: string }
    | { status: 'storage-error', issue: 'STORAGE_WRITE_FAILED' }

export type SaveClearResult
  = | { status: 'cleared' }
    | { status: 'storage-error', issue: 'STORAGE_REMOVE_FAILED' }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort()
  const expected = [...keys].sort()
  return actual.length === expected.length && actual.every((key, index) => key === expected[index])
}

/** Serializes a valid campaign into the one versioned, namespaced save envelope. */
export function serializeSave(state: GameState): string | null {
  const validation = validateGameState(state)
  if (!validation.valid)
    return null

  const envelope: SaveEnvelope = {
    namespace: SAVE_NAMESPACE,
    version: SAVE_VERSION,
    state,
  }
  return JSON.stringify(envelope)
}

/** Writes a campaign save after full state validation. */
export function saveGame(storage: SaveStorage, state: GameState): SaveWriteResult {
  const validation = validateGameState(state)
  if (!validation.valid)
    return { status: 'invalid', issue: 'INVALID_STATE', path: validation.path }

  try {
    storage.setItem(SAVE_KEY, JSON.stringify({
      namespace: SAVE_NAMESPACE,
      version: SAVE_VERSION,
      state,
    } satisfies SaveEnvelope))
    return { status: 'saved' }
  }
  catch {
    return { status: 'storage-error', issue: 'STORAGE_WRITE_FAILED' }
  }
}

/** Reads and validates one campaign save without changing unrelated storage. */
export function loadGame(storage: SaveStorage): SaveLoadResult {
  let raw: string | null
  try {
    raw = storage.getItem(SAVE_KEY)
  }
  catch {
    return { status: 'storage-error', issue: 'STORAGE_READ_FAILED' }
  }

  if (raw === null)
    return { status: 'empty' }

  let value: unknown
  try {
    value = JSON.parse(raw)
  }
  catch {
    return { status: 'invalid', issue: 'MALFORMED_JSON' }
  }

  if (!isRecord(value) || !hasExactKeys(value, ['namespace', 'version', 'state']) || value.namespace !== SAVE_NAMESPACE)
    return { status: 'invalid', issue: 'INVALID_ENVELOPE' }
  if (value.version !== SAVE_VERSION)
    return { status: 'invalid', issue: 'UNSUPPORTED_VERSION' }

  const validation = validateGameState(value.state)
  if (!validation.valid)
    return { status: 'invalid', issue: 'INVALID_STATE', path: validation.path }

  return { status: 'loaded', state: value.state as GameState }
}

/** Removes only the campaign save key. */
export function clearGameSave(storage: SaveStorage): SaveClearResult {
  try {
    storage.removeItem(SAVE_KEY)
    return { status: 'cleared' }
  }
  catch {
    return { status: 'storage-error', issue: 'STORAGE_REMOVE_FAILED' }
  }
}
