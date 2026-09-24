import type { GameCommand, GameState } from '../game'
import type { SaveIssueCode, SaveStorage } from '../save'

import { computed, readonly, shallowRef } from 'vue'

import {
  applyCommand,
  createInitialState,
} from '../game'
import {
  clearGameSave,
  loadGame,
  saveGame,
} from '../save'

export interface UseCampaignOptions {
  /** Storage boundary for campaign persistence. @default browser localStorage */
  storage?: SaveStorage
}

const browserStorage: SaveStorage = {
  getItem: key => globalThis.localStorage.getItem(key),
  setItem: (key, value) => globalThis.localStorage.setItem(key, value),
  removeItem: key => globalThis.localStorage.removeItem(key),
}

function loadFailureMessage(issue: SaveIssueCode): string {
  if (issue === 'STORAGE_READ_FAILED')
    return 'The saved company could not be read. Browser storage is unavailable.'

  return 'The saved company is invalid. Reset the company to remove the saved data.'
}

/**
 * Restores the saved campaign and owns its later state transitions.
 *
 * Successful commands update memory before the save write. A storage failure stays visible
 * through `persistenceError` while the in-memory campaign remains usable.
 */
export function useCampaign(options: UseCampaignOptions = {}) {
  const storage = options.storage ?? browserStorage
  const savedRun = loadGame(storage)
  const currentState = shallowRef<GameState>(createInitialState())
  const persistenceError = shallowRef<string | null>(null)

  if (savedRun.status === 'loaded')
    currentState.value = savedRun.state
  else if (savedRun.status === 'invalid' || savedRun.status === 'storage-error')
    persistenceError.value = loadFailureMessage(savedRun.issue)

  function execute(command: GameCommand) {
    const result = applyCommand(currentState.value, command)
    if (!result.ok)
      return result

    currentState.value = result.state
    const saveResult = saveGame(storage, result.state)
    persistenceError.value = saveResult.status === 'saved'
      ? null
      : 'The company changed, but the save could not be written.'

    return result
  }

  function reset() {
    currentState.value = createInitialState()
    const clearResult = clearGameSave(storage)
    persistenceError.value = clearResult.status === 'cleared'
      ? null
      : 'The company was reset, but its saved run could not be cleared.'

    return clearResult
  }

  return {
    state: computed(() => readonly(currentState.value)),
    persistenceError: computed(() => persistenceError.value),
    execute,
    reset,
  }
}
