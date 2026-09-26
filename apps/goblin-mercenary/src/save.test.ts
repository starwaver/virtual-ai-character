import type { GameCommand, GameState } from './game'
import type { SaveStorage } from './save'

import { describe, expect, it } from 'vitest'

import { applyCommand, createInitialState } from './game'
import {
  clearGameSave,
  loadGame,
  SAVE_KEY,
  SAVE_NAMESPACE,
  SAVE_VERSION,
  saveGame,
} from './save'

class MemoryStorage implements SaveStorage {
  private readonly values = new Map<string, string>()

  getItem(key: string): string | null {
    return this.values.get(key) ?? null
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value)
  }

  removeItem(key: string): void {
    this.values.delete(key)
  }
}

function midEncounterState(): GameState {
  let state = createInitialState()
  const onboarding = applyCommand(state, { type: 'begin-onboarding' })
  if (!onboarding.ok)
    throw new Error(onboarding.error.code)
  state = onboarding.state

  const company = applyCommand(state, { type: 'complete-onboarding' })
  if (!company.ok)
    throw new Error(company.error.code)
  state = company.state

  const selected = applyCommand(state, { type: 'select-contract', contractId: 'moss-road' })
  if (!selected.ok)
    throw new Error(selected.error.code)
  state = selected.state

  const crewSelected = applyCommand(state, { type: 'select-crew', crew: ['mog', 'nix'] })
  if (!crewSelected.ok)
    throw new Error(crewSelected.error.code)
  state = crewSelected.state

  const launched = applyCommand(state, { type: 'launch-encounter' })
  if (!launched.ok)
    throw new Error(launched.error.code)
  state = launched.state

  const action = applyCommand(state, { type: 'strike', actor: 'mog' })
  if (!action.ok)
    throw new Error(action.error.code)
  return action.state
}

function fallenCrewEncounterState(): GameState {
  let state = createInitialState()
  const onboarding = applyCommand(state, { type: 'begin-onboarding' })
  if (!onboarding.ok)
    throw new Error(onboarding.error.code)
  state = onboarding.state

  const company = applyCommand(state, { type: 'complete-onboarding' })
  if (!company.ok)
    throw new Error(company.error.code)
  state = {
    ...company.state,
    crew: {
      ...company.state.crew,
      mog: { ...company.state.crew.mog, health: 2 },
    },
  }

  const commands: GameCommand[] = [
    { type: 'select-contract', contractId: 'black-pit' },
    { type: 'select-crew', crew: ['bomber', 'mog'] },
    { type: 'launch-encounter' },
    { type: 'bomb', actor: 'bomber' },
    { type: 'strike', actor: 'bomber' },
  ]
  for (const command of commands) {
    const result = applyCommand(state, command)
    if (!result.ok)
      throw new Error(result.error.code)
    state = result.state
  }

  return state
}

function unavailableCrewEncounterState(): GameState {
  const state = fallenCrewEncounterState()
  return {
    ...state,
    crew: {
      ...state.crew,
      bomber: { ...state.crew.bomber, health: 0 },
    },
  }
}

describe('goblin Mercenary Company save boundary', () => {
  it('round-trips a mid-encounter state with its action history', () => {
    const storage = new MemoryStorage()
    const state = midEncounterState()
    const saved = saveGame(storage, state)

    expect(saved).toEqual({ status: 'saved' })
    expect(storage.getItem(SAVE_KEY)).toContain(`"namespace":"${SAVE_NAMESPACE}"`)

    const loaded = loadGame(storage)
    expect(loaded.status).toBe('loaded')
    if (loaded.status === 'loaded') {
      expect(loaded.state).toEqual(state)
      expect(loaded.state.phase).toBe('encounter')
      expect(loaded.state.history).toHaveLength(6)
    }
  })

  it('round-trips an encounter where a fallen member remains in the selected crew', () => {
    const storage = new MemoryStorage()
    const state = fallenCrewEncounterState()
    expect(state.phase).toBe('encounter')
    expect(state.activeCrew).toEqual(['bomber', 'mog'])
    expect(state.crew.mog.health).toBe(0)

    expect(saveGame(storage, state)).toEqual({ status: 'saved' })
    expect(loadGame(storage)).toEqual({ status: 'loaded', state })
  })

  // https://github.com/starwaver/virtual-ai-character/issues/7
  // ROOT CAUSE:
  // If both active crew have zero health during an encounter, validation accepts the state.
  // Combat actions then fail with CREW_UNAVAILABLE because no selected member can act.
  // Validation must reject this encounter while allowing a result with fallen crew.
  it('rejects an encounter with no living selected crew (Issue #7)', () => {
    const storage = new MemoryStorage()
    const state = unavailableCrewEncounterState()
    expect(state.phase).toBe('encounter')
    expect(state.activeCrew).toEqual(['bomber', 'mog'])
    expect(state.crew.bomber.health).toBe(0)
    expect(state.crew.mog.health).toBe(0)

    expect(saveGame(storage, state)).toEqual({
      status: 'invalid',
      issue: 'INVALID_STATE',
      path: 'activeCrew',
    })
    expect(storage.getItem(SAVE_KEY)).toBeNull()

    storage.setItem(SAVE_KEY, JSON.stringify({
      namespace: SAVE_NAMESPACE,
      version: SAVE_VERSION,
      state,
    }))
    expect(loadGame(storage)).toEqual({
      status: 'invalid',
      issue: 'INVALID_STATE',
      path: 'activeCrew',
    })
  })

  it('reports malformed and unsupported saves without clearing unrelated storage', () => {
    const storage = new MemoryStorage()
    storage.setItem('other-feature:v1', 'keep this value')
    storage.setItem(SAVE_KEY, '{ malformed')

    expect(loadGame(storage)).toEqual({ status: 'invalid', issue: 'MALFORMED_JSON' })
    expect(storage.getItem('other-feature:v1')).toBe('keep this value')
    expect(storage.getItem(SAVE_KEY)).toBe('{ malformed')

    storage.setItem(SAVE_KEY, JSON.stringify({
      namespace: SAVE_NAMESPACE,
      version: 99,
      state: createInitialState(),
    }))
    expect(loadGame(storage)).toEqual({ status: 'invalid', issue: 'UNSUPPORTED_VERSION' })

    storage.setItem(SAVE_KEY, JSON.stringify({
      namespace: SAVE_NAMESPACE,
      version: 1,
      state: createInitialState(),
      unexpected: true,
    }))
    expect(loadGame(storage)).toEqual({ status: 'invalid', issue: 'INVALID_ENVELOPE' })
    expect(storage.getItem('other-feature:v1')).toBe('keep this value')
  })

  it('rejects invalid domain state before writing and distinguishes invalid resume state', () => {
    const storage = new MemoryStorage()
    const invalidState = createInitialState()
    invalidState.phase = 'preparation'

    expect(saveGame(storage, invalidState)).toEqual({
      status: 'invalid',
      issue: 'INVALID_STATE',
      path: 'preparation',
    })
    expect(storage.getItem(SAVE_KEY)).toBeNull()

    storage.setItem(SAVE_KEY, JSON.stringify({
      namespace: SAVE_NAMESPACE,
      version: SAVE_VERSION,
      state: invalidState,
    }))
    expect(loadGame(storage)).toEqual({
      status: 'invalid',
      issue: 'INVALID_STATE',
      path: 'preparation',
    })

    const extraState = {
      ...createInitialState(),
      unexpected: true,
    }
    expect(saveGame(storage, extraState)).toEqual({ status: 'invalid', issue: 'INVALID_STATE', path: 'state' })
  })

  it('clears only the namespaced campaign key', () => {
    const storage = new MemoryStorage()
    storage.setItem(SAVE_KEY, 'campaign')
    storage.setItem('other-feature:v1', 'keep this value')

    expect(clearGameSave(storage)).toEqual({ status: 'cleared' })
    expect(storage.getItem(SAVE_KEY)).toBeNull()
    expect(storage.getItem('other-feature:v1')).toBe('keep this value')
  })
})
