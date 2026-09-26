import type { GameCommand, GameState } from '../game'
import type { SaveStorage } from '../save'

import { describe, expect, it } from 'vitest'
import { isReadonly } from 'vue'

import { createInitialState } from '../game'
import { loadGame, SAVE_KEY } from '../save'
import { useCampaign } from './use-campaign'

class MemorySaveStorage implements SaveStorage {
  readonly values = new Map<string, string>()
  readFailure = false
  writeFailure = false
  removeFailure = false
  writes = 0

  getItem(key: string): string | null {
    if (this.readFailure)
      throw new Error('read failed')

    return this.values.get(key) ?? null
  }

  setItem(key: string, value: string): void {
    if (this.writeFailure)
      throw new Error('write failed')

    this.writes += 1
    this.values.set(key, value)
  }

  removeItem(key: string): void {
    if (this.removeFailure)
      throw new Error('remove failed')

    this.values.delete(key)
  }
}

function execute(controller: ReturnType<typeof useCampaign>, command: GameCommand): GameState {
  const result = controller.execute(command)
  expect(result.ok).toBe(true)
  return result.state
}

function startPreparation(controller: ReturnType<typeof useCampaign>): void {
  execute(controller, { type: 'begin-onboarding' })
  execute(controller, { type: 'complete-onboarding' })
  execute(controller, { type: 'select-contract', contractId: 'bell-foundry' })
}

describe('useCampaign', () => {
  it('starts with a fresh company when storage has no saved run', () => {
    const controller = useCampaign({ storage: new MemorySaveStorage() })

    expect(controller.state.value).toEqual(createInitialState())
    expect(controller.persistenceError.value).toBeNull()
  })

  it('exposes campaign state as deeply read-only', () => {
    const controller = useCampaign({ storage: new MemorySaveStorage() })

    expect(isReadonly(controller.state)).toBe(true)
    expect(isReadonly(controller.state.value)).toBe(true)
    expect(isReadonly(controller.state.value.resources)).toBe(true)
    expect(isReadonly(controller.state.value.crew.mog)).toBe(true)
  })

  it('loads a saved company when the controller starts', () => {
    const storage = new MemorySaveStorage()
    const firstController = useCampaign({ storage })
    const savedState = execute(firstController, { type: 'begin-onboarding' })
    const restoredController = useCampaign({ storage })

    expect(restoredController.state.value).toEqual(savedState)
    expect(restoredController.state.value.phase).toBe('onboarding')
  })

  it('saves every successful command and leaves failed commands unsaved', () => {
    const storage = new MemorySaveStorage()
    const controller = useCampaign({ storage })

    execute(controller, { type: 'begin-onboarding' })
    expect(loadGame(storage)).toMatchObject({ status: 'loaded', state: { phase: 'onboarding' } })

    execute(controller, { type: 'complete-onboarding' })
    expect(loadGame(storage)).toMatchObject({ status: 'loaded', state: { phase: 'company' } })

    const writesBeforeFailure = storage.writes
    const failure = controller.execute({ type: 'launch-encounter' })

    expect(failure.ok).toBe(false)
    expect(storage.writes).toBe(writesBeforeFailure)
    expect(loadGame(storage)).toMatchObject({ status: 'loaded', state: { phase: 'company' } })
  })

  it('restores the current encounter after the page reloads', () => {
    const storage = new MemorySaveStorage()
    const controller = useCampaign({ storage })
    startPreparation(controller)
    execute(controller, { type: 'select-crew', crew: ['mog', 'healer'] })
    const encounterState = execute(controller, { type: 'launch-encounter' })

    const restoredController = useCampaign({ storage })

    expect(encounterState.phase).toBe('encounter')
    expect(restoredController.state.value).toEqual(encounterState)
    expect(restoredController.state.value.encounter?.enemyHealth).toBe(9)
  })

  // https://github.com/starwaver/virtual-ai-character/issues/7
  it('issue #7 saves each empty, partial, and full crew selection', () => {
    const storage = new MemorySaveStorage()
    let controller = useCampaign({ storage })
    startPreparation(controller)
    execute(controller, { type: 'select-crew', crew: ['mog'] })
    expect(controller.state.value.activeCrew).toEqual(['mog'])

    expect(loadGame(storage)).toMatchObject({
      status: 'loaded',
      state: { phase: 'preparation', activeCrew: ['mog'] },
    })

    controller = useCampaign({ storage })
    expect(controller.state.value.activeCrew).toEqual(['mog'])

    execute(controller, { type: 'select-crew', crew: ['mog', 'healer'] })
    expect(loadGame(storage)).toMatchObject({
      status: 'loaded',
      state: { phase: 'preparation', activeCrew: ['mog', 'healer'] },
    })
    expect(controller.state.value.activeCrew).toEqual(['mog', 'healer'])

    controller = useCampaign({ storage })
    expect(controller.state.value.activeCrew).toEqual(['mog', 'healer'])

    execute(controller, { type: 'select-crew', crew: ['healer'] })
    expect(controller.state.value.activeCrew).toEqual(['healer'])
    expect(loadGame(storage)).toMatchObject({
      status: 'loaded',
      state: { phase: 'preparation', activeCrew: ['healer'] },
    })

    controller = useCampaign({ storage })
    expect(controller.state.value.activeCrew).toEqual(['healer'])

    execute(controller, { type: 'select-crew', crew: [] })
    expect(controller.state.value.activeCrew).toEqual([])
    expect(loadGame(storage)).toMatchObject({
      status: 'loaded',
      state: { phase: 'preparation', activeCrew: [] },
    })

    const afterDeselectController = useCampaign({ storage })
    expect(afterDeselectController.state.value.activeCrew).toEqual([])
  })

  it('resets a live run and clears only the game save', () => {
    const storage = new MemorySaveStorage()
    const controller = useCampaign({ storage })
    storage.setItem('other-game:save', 'keep')
    startPreparation(controller)
    execute(controller, { type: 'select-crew', crew: ['mog', 'healer'] })
    execute(controller, { type: 'launch-encounter' })

    const resetResult = controller.reset()

    expect(resetResult.status).toBe('cleared')
    expect(controller.state.value).toEqual(createInitialState())
    expect(storage.getItem(SAVE_KEY)).toBeNull()
    expect(storage.getItem('other-game:save')).toBe('keep')
  })

  it('shows read errors and uses a fresh company when storage cannot be read', () => {
    const storage = new MemorySaveStorage()
    storage.readFailure = true

    const controller = useCampaign({ storage })

    expect(controller.state.value.phase).toBe('start')
    expect(controller.persistenceError.value).toContain('could not be read')
  })

  it('shows write errors while keeping the accepted command in memory', () => {
    const storage = new MemorySaveStorage()
    const controller = useCampaign({ storage })
    storage.writeFailure = true

    const result = controller.execute({ type: 'begin-onboarding' })

    expect(result.ok).toBe(true)
    expect(controller.state.value.phase).toBe('onboarding')
    expect(controller.persistenceError.value).toContain('could not be written')
  })

  it('shows clear errors while resetting the current company', () => {
    const storage = new MemorySaveStorage()
    const controller = useCampaign({ storage })
    startPreparation(controller)
    storage.removeFailure = true

    const result = controller.reset()

    expect(result.status).toBe('storage-error')
    expect(controller.state.value.phase).toBe('start')
    expect(controller.persistenceError.value).toContain('could not be cleared')
    expect(loadGame(storage)).toMatchObject({ status: 'loaded', state: { phase: 'preparation' } })
  })
})
