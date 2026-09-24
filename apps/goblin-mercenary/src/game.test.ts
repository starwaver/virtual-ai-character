import type { ContractId, CrewId, GameCommand, GameState } from './game'

import { describe, expect, it } from 'vitest'

import {
  applyCommand,
  createInitialState,
  getContracts,
  getCrewRoster,
  getNextThreatTarget,
  validateGameState,
} from './game'

function apply(state: GameState, command: GameCommand): GameState {
  const result = applyCommand(state, command)
  if (!result.ok)
    throw new Error(`Command failed: ${result.error.code}`)
  return result.state
}

function startCompany(): GameState {
  let state = createInitialState()
  state = apply(state, { type: 'begin-onboarding' })
  return apply(state, { type: 'complete-onboarding' })
}

function prepare(
  contractId: ContractId = 'moss-road',
  crew: CrewId[] = ['mog', 'bomber'],
  company: GameState = startCompany(),
): GameState {
  const selected = apply(company, { type: 'select-contract', contractId })
  return apply(selected, { type: 'select-crew', crew })
}

function launch(state: GameState): GameState {
  return apply(state, { type: 'launch-encounter' })
}

function companyWithWoundedMog(): GameState {
  const company = startCompany()
  return {
    ...company,
    crew: {
      ...company.crew,
      mog: { ...company.crew.mog, health: 2 },
    },
  }
}

describe('goblin Mercenary Company rules', () => {
  it('guides a fresh Captain from start through onboarding to the company', () => {
    const initial = createInitialState()
    expect(initial.phase).toBe('start')
    expect(validateGameState(initial)).toEqual({ valid: true })

    const onboarding = apply(initial, { type: 'begin-onboarding' })
    expect(onboarding.phase).toBe('onboarding')
    expect(onboarding.history.at(-1)?.phaseBefore).toBe('start')

    const company = apply(onboarding, { type: 'complete-onboarding' })
    expect(company.phase).toBe('company')
    expect(company.history.at(-1)?.phaseAfter).toBe('company')
  })

  it('exposes deterministic contracts and keeps support roles distinct', () => {
    const contracts = getContracts()
    const roster = getCrewRoster()

    expect(contracts.map(contract => contract.id)).toEqual(['moss-road', 'bell-foundry', 'black-pit'])
    expect(contracts.map(contract => contract.risk)).toEqual(['low', 'medium', 'high'])
    expect(contracts.every(contract => contract.recommendedPreparation.length > 0)).toBe(true)
    expect(roster.map(member => member.id)).toEqual(['captain', 'nix', 'mog', 'healer', 'bomber'])
    expect(roster.find(member => member.id === 'nix')?.roles).toEqual(['lieutenant', 'quartermaster'])
    expect(roster.find(member => member.id === 'mog')?.roles).toEqual(['fighter'])
    expect(roster.find(member => member.id === 'healer')?.roles).toEqual(['healer'])
    expect(roster.find(member => member.id === 'bomber')?.roles).toEqual(['bomber'])
  })

  it('keeps transitions immutable and rejects illegal preparation commands', () => {
    const initial = createInitialState()
    const illegal = applyCommand(initial, { type: 'launch-encounter' })

    expect(illegal.ok).toBe(false)
    if (!illegal.ok)
      expect(illegal.error.code).toBe('ILLEGAL_PHASE')
    expect(initial.phase).toBe('start')
    expect(initial.history).toHaveLength(0)

    const prepared = prepare()
    const duplicate = applyCommand(prepared, { type: 'select-crew', crew: ['mog', 'mog'] })
    expect(duplicate.ok).toBe(false)
    if (!duplicate.ok)
      expect(duplicate.error.code).toBe('DUPLICATE_CREW')

    const tooMany = applyCommand(prepared, { type: 'select-crew', crew: ['captain', 'nix', 'mog'] })
    expect(tooMany.ok).toBe(false)
    if (!tooMany.ok)
      expect(tooMany.error.code).toBe('CREW_LIMIT')

    const company = startCompany()
    const unavailableCompany = {
      ...company,
      crew: {
        ...company.crew,
        mog: { ...company.crew.mog, health: 0 },
      },
    }
    const unavailableResult = applyCommand(
      apply(unavailableCompany, { type: 'select-contract', contractId: 'moss-road' }),
      { type: 'select-crew', crew: ['mog', 'healer'] },
    )
    expect(unavailableResult.ok).toBe(false)
    if (!unavailableResult.ok)
      expect(unavailableResult.error.code).toBe('CREW_UNAVAILABLE')
  })

  it('records empty, partial, and full crew selections in valid preparation state', () => {
    const preparation = apply(startCompany(), { type: 'select-contract', contractId: 'moss-road' })

    const empty = apply(preparation, { type: 'select-crew', crew: [] })
    expect(empty.activeCrew).toEqual([])
    expect(empty.history.at(-1)?.command).toEqual({ type: 'select-crew', crew: [] })
    expect(validateGameState(empty)).toEqual({ valid: true })

    const partial = apply(empty, { type: 'select-crew', crew: ['mog'] })
    expect(partial.activeCrew).toEqual(['mog'])
    expect(partial.history.at(-1)?.command).toEqual({ type: 'select-crew', crew: ['mog'] })
    expect(validateGameState(partial)).toEqual({ valid: true })

    const full = apply(partial, { type: 'select-crew', crew: ['mog', 'healer'] })
    expect(full.activeCrew).toEqual(['mog', 'healer'])
    expect(validateGameState(full)).toEqual({ valid: true })
  })

  // ROOT CAUSE:
  // Selecting a contract used to trap the player in preparation until they launched it.
  // Returning to the board must clear only the pending contract and crew choice.
  it('returns from preparation to the contract board without losing supplies', () => {
    const prepared = prepare('moss-road', ['mog', 'bomber'])
    const supplied = apply(prepared, { type: 'buy-rations', amount: 1 })
    const returned = apply(supplied, { type: 'leave-preparation' })

    expect(returned.phase).toBe('company')
    expect(returned.selectedContract).toBeNull()
    expect(returned.activeCrew).toEqual([])
    expect(returned.resources).toEqual(supplied.resources)
    expect(validateGameState(returned)).toEqual({ valid: true })
    expect(apply(returned, { type: 'select-contract', contractId: 'bell-foundry' }).phase).toBe('preparation')
  })

  it('blocks launch until exactly two healthy crew members are selected', () => {
    const preparation = apply(startCompany(), { type: 'select-contract', contractId: 'moss-road' })
    const empty = apply(preparation, { type: 'select-crew', crew: [] })
    const emptyLaunch = applyCommand(empty, { type: 'launch-encounter' })
    expect(emptyLaunch.ok).toBe(false)
    if (!emptyLaunch.ok)
      expect(emptyLaunch.error.code).toBe('CREW_REQUIRED')

    const partial = apply(empty, { type: 'select-crew', crew: ['mog'] })
    const partialLaunch = applyCommand(partial, { type: 'launch-encounter' })
    expect(partialLaunch.ok).toBe(false)
    if (!partialLaunch.ok)
      expect(partialLaunch.error.code).toBe('CREW_REQUIRED')

    const full = apply(partial, { type: 'select-crew', crew: ['mog', 'healer'] })
    expect(launch(full).phase).toBe('encounter')
  })

  it('rejects unaffordable supplies and keeps resources non-negative', () => {
    const prepared = prepare()
    const unaffordable = applyCommand(prepared, { type: 'buy-rations', amount: 5 })

    expect(unaffordable.ok).toBe(false)
    if (!unaffordable.ok)
      expect(unaffordable.error.code).toBe('UNAFFORDABLE')

    const supplied = apply(prepared, { type: 'buy-rations', amount: 2 })
    expect(supplied.resources.coin).toBe(4)
    expect(supplied.resources.rations).toBe(3)
    expect(Object.values(supplied.resources).every(value => value >= 0)).toBe(true)
  })

  it('makes healing Mog safer than taking bomber offense when Mog is badly wounded', () => {
    const injuredCompany = companyWithWoundedMog()
    expect(validateGameState(injuredCompany)).toEqual({ valid: true })

    let healerState = launch(prepare('black-pit', ['mog', 'healer'], injuredCompany))
    expect(healerState.encounter?.healingCharges).toBe(1)
    expect(healerState.encounter?.bombCharges).toBe(0)
    expect(getNextThreatTarget(healerState)).toBe('mog')

    healerState = apply(healerState, { type: 'heal', actor: 'healer', target: 'mog' })
    expect(healerState.crew.mog.health).toBe(4)
    expect(healerState.encounter?.enemyHealth).toBe(12)
    expect(getNextThreatTarget(healerState)).toBe('healer')

    let bomberState = launch(prepare('black-pit', ['mog', 'bomber'], injuredCompany))
    expect(bomberState.encounter?.healingCharges).toBe(0)
    expect(bomberState.encounter?.bombCharges).toBe(1)
    expect(getNextThreatTarget(bomberState)).toBe('mog')

    bomberState = apply(bomberState, { type: 'bomb', actor: 'bomber' })
    expect(bomberState.encounter?.enemyHealth).toBe(6)
    expect(bomberState.crew.mog.health).toBe(0)
    expect(getNextThreatTarget(bomberState)).toBe('bomber')
    expect(validateGameState(bomberState)).toEqual({ valid: true })

    while (healerState.phase === 'encounter')
      healerState = apply(healerState, { type: 'strike', actor: 'mog' })
    expect(healerState.result?.outcome).toBe('victory')
    expect(healerState.crew.mog.health).toBeGreaterThan(0)
  })

  it('uses the bomber charge to shorten a healthy crew fight', () => {
    const bombState = apply(launch(prepare('moss-road', ['mog', 'bomber'])), { type: 'bomb', actor: 'bomber' })
    expect(bombState.phase).toBe('results')
    expect(bombState.result?.rounds).toBe(1)

    let strikeState = launch(prepare('moss-road', ['mog', 'bomber']))
    strikeState = apply(strikeState, { type: 'strike', actor: 'mog' })
    strikeState = apply(strikeState, { type: 'strike', actor: 'mog' })
    expect(strikeState.phase).toBe('results')
    expect(strikeState.result?.rounds).toBe(2)

    const unavailableBomb = applyCommand(launch(prepare('moss-road', ['mog', 'healer'])), { type: 'bomb', actor: 'mog' })
    expect(unavailableBomb.ok).toBe(false)
    if (!unavailableBomb.ok)
      expect(unavailableBomb.error.code).toBe('ACTION_UNAVAILABLE')
  })

  it('applies rewards once, recovers the roster, and reaches a campaign win', () => {
    let state = startCompany()
    for (const contractId of ['moss-road', 'bell-foundry', 'black-pit'] as const) {
      state = apply(state, { type: 'select-contract', contractId })
      state = apply(state, { type: 'select-crew', crew: ['mog', 'bomber'] })
      state = apply(state, { type: 'launch-encounter' })
      while (state.phase === 'encounter') {
        state = apply(state, state.encounter?.bombCharges === 1
          ? { type: 'bomb', actor: 'bomber' }
          : { type: 'strike', actor: 'mog' })
      }
      expect(state.phase).toBe('results')
      state = apply(state, { type: 'claim-reward' })
      const duplicateReward = applyCommand(state, { type: 'claim-reward' })
      expect(duplicateReward.ok).toBe(false)
      if (!duplicateReward.ok)
        expect(duplicateReward.error.code).toBe('REWARD_ALREADY_APPLIED')
      state = apply(state, { type: 'continue-campaign' })
    }

    expect(state.phase).toBe('terminal')
    expect(state.status).toBe('won')
    expect(state.completedContracts).toEqual(['moss-road', 'bell-foundry', 'black-pit'])
    expect(state.resources).toEqual({ coin: 25, rations: 3, reputation: 6 })
    expect(validateGameState(state)).toEqual({ valid: true })
  })

  it('reaches a loss and supports a deterministic restart', () => {
    let state = launch(prepare('black-pit', ['captain', 'nix']))
    while (state.phase === 'encounter') {
      const actor = state.crew.nix.health > 0 ? 'nix' : 'captain'
      state = apply(state, { type: 'strike', actor })
    }

    expect(state.phase).toBe('results')
    expect(state.result?.outcome).toBe('defeat')
    expect(validateGameState(state)).toEqual({ valid: true })
    state = apply(state, { type: 'continue-campaign' })
    expect(state.phase).toBe('terminal')
    expect(state.status).toBe('lost')

    state = apply(state, { type: 'restart-campaign' })
    expect(state).toEqual(createInitialState())
  })

  // https://github.com/starwaver/virtual-ai-character/issues/7
  it('issue #7 keeps fallen active crew in valid encounter results', () => {
    let state = launch(prepare('black-pit', ['mog', 'bomber'], companyWithWoundedMog()))
    state = apply(state, { type: 'bomb', actor: 'bomber' })

    expect(state.phase).toBe('encounter')
    expect(state.crew.mog.health).toBe(0)
    expect(validateGameState(state)).toEqual({ valid: true })

    while (state.phase === 'encounter')
      state = apply(state, { type: 'strike', actor: 'bomber' })
    expect(state.phase).toBe('results')
    expect(state.result?.outcome).toBe('victory')
    expect(validateGameState(state)).toEqual({ valid: true })

    state = apply(state, { type: 'claim-reward' })
    state = apply(state, { type: 'continue-campaign' })
    expect(state.phase).toBe('company')
    expect(state.crew.mog.health).toBe(2)
    state = apply(state, { type: 'select-contract', contractId: 'bell-foundry' })
    state = apply(state, { type: 'select-crew', crew: ['mog', 'healer'] })
    expect(state.activeCrew).toEqual(['mog', 'healer'])
  })
})
