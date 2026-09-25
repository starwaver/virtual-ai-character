import type { CrewId, GameCommand, GameState } from '../game'

import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-vue'
import { defineComponent, h, shallowRef } from 'vue'

import EncounterScreen from './encounter-screen.vue'
import ResultsScreen from './results-screen.vue'

import { applyCommand, createInitialState } from '../game'

import '@unocss/reset/tailwind.css'
import '@proj-airi/ui/main.css'
import '../styles.css'
import 'uno.css'

function apply(state: GameState, command: GameCommand) {
  const result = applyCommand(state, command)
  if (!result.ok)
    throw new Error(result.error.code)
  return result.state
}

function encounter(crew: CrewId[] = ['mog', 'healer']) {
  let state = createInitialState()
  const commands: GameCommand[] = [
    { type: 'begin-onboarding' },
    { type: 'complete-onboarding' },
    { type: 'select-contract', contractId: 'black-pit' },
    { type: 'select-crew', crew },
    { type: 'launch-encounter' },
  ]
  for (const command of commands)
    state = apply(state, command)
  return state
}

function renderEncounter(initial: GameState) {
  const state = shallowRef(initial)
  const screen = render(defineComponent({
    setup: () => () => h(state.value.phase === 'encounter' ? EncounterScreen : ResultsScreen, {
      state: state.value,
      onCommand: (command: GameCommand) => { state.value = apply(state.value, command) },
    }),
  }))
  return { screen, state }
}

describe('graphical encounter', () => {
  // https://github.com/starwaver/virtual-ai-character/issues/9
  it('keeps strike commands deterministic and shows health and threat in the scene', async () => {
    const initial = encounter()
    const { screen, state } = renderEncounter(initial)
    const battlefield = screen.getByRole('region', { name: 'Battlefield' })
    await expect.element(battlefield.getByRole('meter', { name: 'Mog health', exact: true })).toHaveAttribute('aria-valuenow', '10')
    const strike = battlefield.getByRole('button', { name: 'Strike with Mog', exact: true })
    await strike.click()
    expect(state.value).toEqual(apply(initial, { type: 'strike', actor: 'mog' }))
    await expect.element(strike).toHaveFocus()
    await expect.element(battlefield.getByRole('meter', { name: 'Black Pit Warlord health' })).toHaveAttribute('aria-valuenow', '9')
    await expect.element(battlefield.getByRole('meter', { name: 'Mog health', exact: true })).toHaveAttribute('aria-valuenow', '8')
    await expect.element(battlefield.getByRole('status')).toHaveTextContent('Mog · Strike · 3 damage')
    await expect.element(battlefield.getByRole('article', { name: 'Mara', exact: true })).toHaveTextContent('Next threat · 2')
  })

  it('heals the named target with the existing command and displays the changed health', async () => {
    const initial = apply(encounter(), { type: 'strike', actor: 'mog' })
    const { screen, state } = renderEncounter(initial)
    const heal = screen.getByRole('button', { name: 'Heal Mog · 8 / 10' })
    heal.element().focus()
    await expect.element(screen.getByRole('article', { name: 'Mog', exact: true })).toHaveClass('battle-unit-selected')
    await heal.click()
    await expect.element(screen.getByRole('article', { name: 'Mog', exact: true })).not.toHaveClass('battle-unit-selected')
    expect(state.value).toEqual(apply(initial, { type: 'heal', actor: 'healer', target: 'mog' }))
    const battlefield = screen.getByRole('region', { name: 'Battlefield' })
    await expect.element(battlefield.getByRole('meter', { name: 'Mog health', exact: true })).toHaveAttribute('aria-valuenow', '10')
    await expect.element(battlefield.getByRole('status')).toHaveTextContent('Mara · Heal Mog')
    await expect.element(screen.getByText('Mara has used her heal.')).toBeVisible()
  })

  it('spends the existing bomb once and disables the used action', async () => {
    const initial = encounter(['mog', 'bomber'])
    const { screen, state } = renderEncounter(initial)
    const bomb = screen.getByRole('button', { name: 'Throw Grit’s bomb' })
    await bomb.click()
    expect(state.value).toEqual(apply(initial, { type: 'bomb', actor: 'bomber' }))
    await expect.element(bomb).toBeDisabled()
    await expect.element(screen.getByRole('region', { name: 'Battlefield' }).getByRole('status')).toHaveTextContent('Grit · Bomb · 6 damage')
  })

  it('keeps fallen crew on the battlefield and disables their strike', async () => {
    let initial = encounter(['nix', 'healer'])
    // Repeated weak strikes reach a real fallen-crew state without fixture mutations.
    for (let turn = 0; turn < 7; turn++)
      initial = apply(initial, { type: 'strike', actor: 'nix' })
    const { screen } = renderEncounter(initial)
    const battlefield = screen.getByRole('region', { name: 'Battlefield' })
    await expect.element(battlefield.getByRole('article', { name: 'Nix', exact: true })).toHaveTextContent('Out of action')
    await expect.element(battlefield.getByRole('button', { name: 'Strike with Nix' })).toBeDisabled()
    await expect.element(battlefield.getByRole('button', { name: 'Strike with Mara' })).toBeEnabled()
  })

  it('shows the defeated enemy after a finishing strike without adding a combat turn', async () => {
    let initial = encounter()
    for (let turn = 0; turn < 3; turn++)
      initial = apply(initial, { type: 'strike', actor: 'mog' })
    const { screen, state } = renderEncounter(initial)
    await screen.getByRole('button', { name: 'Strike with Mog' }).click()
    expect(state.value).toEqual(apply(initial, { type: 'strike', actor: 'mog' }))
    await expect.element(screen.getByRole('region', { name: 'Battlefield' }).getByText('Defeated', { exact: true })).toBeVisible()
    await expect.element(screen.getByRole('button', { name: 'Claim the contract pay' })).toBeVisible()
  })
})
