export const GAME_VERSION = 2 as const

export const CREW_IDS = ['captain', 'nix', 'mog', 'healer', 'bomber'] as const
export type CrewId = typeof CREW_IDS[number]

export const CONTRACT_IDS = ['moss-road', 'bell-foundry', 'black-pit'] as const
export type ContractId = typeof CONTRACT_IDS[number]

export type GamePhase = 'start' | 'onboarding' | 'company' | 'preparation' | 'encounter' | 'results' | 'terminal'
export type CampaignStatus = 'active' | 'won' | 'lost'
export type EncounterOutcome = 'victory' | 'defeat'
export type CrewRole = 'captain' | 'lieutenant' | 'quartermaster' | 'fighter' | 'healer' | 'bomber'
export type ContractRisk = 'low' | 'medium' | 'high'
export type ResourceName = 'coin' | 'rations' | 'reputation'

export interface Resources {
  coin: number
  rations: number
  reputation: number
}

export interface CrewDefinition {
  id: CrewId
  name: string
  roles: readonly CrewRole[]
  maxHealth: number
}

export interface CrewState extends CrewDefinition {
  roles: CrewRole[]
  health: number
}

export interface ContractDefinition {
  id: ContractId
  name: string
  description: string
  risk: ContractRisk
  recommendedPreparation: string
  enemyName: string
  enemyHealth: number
  enemyAttack: number
  rationCost: number
  rewards: Resources
}

export interface EncounterState {
  contractId: ContractId
  enemyHealth: number
  enemyMaxHealth: number
  round: number
  healingCharges: number
  bombCharges: number
}

export interface CampaignResult {
  outcome: EncounterOutcome
  contractId: ContractId
  rounds: number
  rewards: Resources
  rewardApplied: boolean
}

export type GameCommand
  = | { type: 'begin-onboarding' }
    | { type: 'complete-onboarding' }
    | { type: 'select-contract', contractId: ContractId }
    | { type: 'leave-preparation' }
    | { type: 'select-crew', crew: CrewId[] }
    | { type: 'buy-rations', amount: number }
    | { type: 'launch-encounter' }
    | { type: 'strike', actor: CrewId }
    | { type: 'heal', actor: CrewId, target: CrewId }
    | { type: 'bomb', actor: CrewId }
    | { type: 'claim-reward' }
    | { type: 'continue-campaign' }
    | { type: 'restart-campaign' }

export interface ActionRecord {
  sequence: number
  command: GameCommand
  phaseBefore: GamePhase
  phaseAfter: GamePhase
}

export interface GameState {
  version: typeof GAME_VERSION
  phase: GamePhase
  status: CampaignStatus
  resources: Resources
  crew: Record<CrewId, CrewState>
  activeCrew: CrewId[]
  selectedContract: ContractId | null
  completedContracts: ContractId[]
  encounter: EncounterState | null
  result: CampaignResult | null
  history: ActionRecord[]
}

export type CommandErrorCode
  = | 'ILLEGAL_PHASE'
    | 'INVALID_CONTRACT'
    | 'CONTRACT_COMPLETED'
    | 'DUPLICATE_CREW'
    | 'CREW_LIMIT'
    | 'CREW_UNAVAILABLE'
    | 'INVALID_CREW'
    | 'INVALID_AMOUNT'
    | 'UNAFFORDABLE'
    | 'CREW_REQUIRED'
    | 'ACTION_UNAVAILABLE'
    | 'INVALID_TARGET'
    | 'TARGET_FULL_HEALTH'
    | 'REWARD_PENDING'
    | 'REWARD_ALREADY_APPLIED'
    | 'NO_RESULT'

export interface CommandError {
  code: CommandErrorCode
}

export interface CommandEvent {
  type:
    | 'onboarding-started'
    | 'onboarding-completed'
    | 'contract-selected'
    | 'preparation-left'
    | 'crew-selected'
    | 'supplies-purchased'
    | 'encounter-started'
    | 'action-resolved'
    | 'victory'
    | 'defeat'
    | 'reward-applied'
    | 'campaign-continued'
    | 'campaign-restarted'
}

export interface CommandSuccess {
  ok: true
  state: GameState
  event: CommandEvent
}

export interface CommandFailure {
  ok: false
  state: GameState
  error: CommandError
}

export type CommandResult = CommandSuccess | CommandFailure

export type StateValidationResult
  = | { valid: true }
    | { valid: false, code: 'INVALID_STATE', path: string }

const CREW_DEFINITIONS: Record<CrewId, CrewDefinition> = {
  captain: {
    id: 'captain',
    name: 'Captain of the Brass Button',
    roles: ['captain'],
    maxHealth: 8,
  },
  nix: {
    id: 'nix',
    name: 'Nix',
    roles: ['lieutenant', 'quartermaster'],
    maxHealth: 7,
  },
  mog: {
    id: 'mog',
    name: 'Mog',
    roles: ['fighter'],
    maxHealth: 10,
  },
  healer: {
    id: 'healer',
    name: 'Mara',
    roles: ['healer'],
    maxHealth: 7,
  },
  bomber: {
    id: 'bomber',
    name: 'Grit',
    roles: ['bomber'],
    maxHealth: 7,
  },
}

const CONTRACTS: readonly ContractDefinition[] = [
  {
    id: 'moss-road',
    name: 'Moss Road Escort',
    description: 'Protect a mushroom cart through the old moss road.',
    risk: 'low',
    recommendedPreparation: 'Bring Mog for a fast, safe escort.',
    enemyName: 'Roadside Goblins',
    enemyHealth: 6,
    enemyAttack: 1,
    rationCost: 1,
    rewards: { coin: 4, rations: 1, reputation: 1 },
  },
  {
    id: 'bell-foundry',
    name: 'Bell Foundry Break-In',
    description: 'Take back the company bell from a guarded foundry.',
    risk: 'medium',
    recommendedPreparation: 'If the front line is hurt, bring a healer.',
    enemyName: 'Foundry Brute',
    enemyHealth: 9,
    enemyAttack: 2,
    rationCost: 1,
    rewards: { coin: 5, rations: 2, reputation: 2 },
  },
  {
    id: 'black-pit',
    name: 'Black Pit Muster',
    description: 'Break the warlord line before it reaches Brass Button town.',
    risk: 'high',
    recommendedPreparation: 'Bring Mara to protect wounded fighters.',
    enemyName: 'Black Pit Warlord',
    enemyHealth: 12,
    enemyAttack: 2,
    rationCost: 1,
    rewards: { coin: 8, rations: 2, reputation: 3 },
  },
]

/** Returns the fixed contract list used by every campaign run. */
export function getContracts(): ContractDefinition[] {
  return CONTRACTS.map(contract => ({
    ...contract,
    rewards: { ...contract.rewards },
  }))
}

/** Returns the fixed roster with its role labels and maximum health. */
export function getCrewRoster(): CrewDefinition[] {
  return CREW_IDS.map(id => ({
    ...CREW_DEFINITIONS[id],
    roles: [...CREW_DEFINITIONS[id].roles],
  }))
}

function createCrewState(id: CrewId): CrewState {
  const definition = CREW_DEFINITIONS[id]
  return {
    ...definition,
    roles: [...definition.roles],
    health: definition.maxHealth,
  }
}

/** Creates a new campaign with a full roster and enough supplies for the first contract. */
export function createInitialState(): GameState {
  return {
    version: GAME_VERSION,
    phase: 'start',
    status: 'active',
    resources: { coin: 8, rations: 1, reputation: 0 },
    crew: {
      captain: createCrewState('captain'),
      nix: createCrewState('nix'),
      mog: createCrewState('mog'),
      healer: createCrewState('healer'),
      bomber: createCrewState('bomber'),
    },
    activeCrew: [],
    selectedContract: null,
    completedContracts: [],
    encounter: null,
    result: null,
    history: [],
  }
}

function isCrewId(value: unknown): value is CrewId {
  return typeof value === 'string' && (CREW_IDS as readonly string[]).includes(value)
}

function isContractId(value: unknown): value is ContractId {
  return typeof value === 'string' && (CONTRACT_IDS as readonly string[]).includes(value)
}

function contractFor(id: ContractId): ContractDefinition {
  return CONTRACTS.find(contract => contract.id === id) as ContractDefinition
}

function isActiveCrew(state: GameState, id: CrewId): boolean {
  return state.activeCrew.includes(id) && state.crew[id].health > 0
}

function hasRole(state: GameState, id: CrewId, role: CrewRole): boolean {
  return state.crew[id].roles.includes(role)
}

function isPositiveSafeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0
}

function failure(state: GameState, code: CommandErrorCode): CommandFailure {
  return { ok: false, state, error: { code } }
}

function commit(
  state: GameState,
  command: GameCommand,
  changes: Partial<Omit<GameState, 'history'>>,
  event: CommandEvent,
): CommandSuccess {
  const phaseAfter = changes.phase ?? state.phase
  return {
    ok: true,
    state: {
      ...state,
      ...changes,
      history: [
        ...state.history,
        {
          sequence: state.history.length,
          command,
          phaseBefore: state.phase,
          phaseAfter,
        },
      ],
    },
    event,
  }
}

function crewAfterDamage(state: GameState, target: CrewId, damage: number): Record<CrewId, CrewState> {
  return {
    ...state.crew,
    [target]: {
      ...state.crew[target],
      health: Math.max(0, state.crew[target].health - damage),
    },
  }
}

function crewAfterHealing(state: GameState, target: CrewId, amount: number): Record<CrewId, CrewState> {
  return {
    ...state.crew,
    [target]: {
      ...state.crew[target],
      health: Math.min(state.crew[target].maxHealth, state.crew[target].health + amount),
    },
  }
}

function livingCrewIds(crew: Record<CrewId, CrewState>, activeCrew: CrewId[]): CrewId[] {
  return activeCrew.filter(id => crew[id].health > 0)
}

function chooseThreatTarget(crew: Record<CrewId, CrewState>, activeCrew: CrewId[], round: number): CrewId | null {
  const living = livingCrewIds(crew, activeCrew)
  if (living.length === 0)
    return null

  return living[round % living.length]
}

/** Returns the next living crew member that the deterministic encounter threat will attack. */
export function getNextThreatTarget(state: GameState): CrewId | null {
  if (state.phase !== 'encounter' || state.encounter === null)
    return null

  return chooseThreatTarget(state.crew, state.activeCrew, state.encounter.round)
}

function resultFor(
  encounter: EncounterState,
  outcome: EncounterOutcome,
): CampaignResult {
  const contract = contractFor(encounter.contractId)
  return {
    outcome,
    contractId: encounter.contractId,
    rounds: encounter.round,
    rewards: { ...contract.rewards },
    rewardApplied: false,
  }
}

function resolveAction(
  state: GameState,
  command: Extract<GameCommand, { type: 'strike' | 'heal' | 'bomb' }>,
  crew: Record<CrewId, CrewState>,
  encounter: EncounterState,
): CommandResult {
  const contract = contractFor(encounter.contractId)
  const actor = command.actor
  let nextCrew = crew
  let nextEncounter = encounter

  if (command.type === 'strike') {
    const damage = actor === 'mog' ? 3 : actor === 'captain' || actor === 'bomber' ? 2 : 1
    nextEncounter = { ...nextEncounter, enemyHealth: Math.max(0, encounter.enemyHealth - damage) }
  }

  if (command.type === 'bomb') {
    nextEncounter = {
      ...nextEncounter,
      bombCharges: encounter.bombCharges - 1,
      enemyHealth: Math.max(0, encounter.enemyHealth - 6),
    }
  }

  if (command.type === 'heal') {
    nextCrew = crewAfterHealing(state, command.target, 4)
    nextEncounter = {
      ...nextEncounter,
      healingCharges: encounter.healingCharges - 1,
    }
  }

  if (nextEncounter.enemyHealth === 0) {
    return commit(
      state,
      command,
      {
        phase: 'results',
        crew: nextCrew,
        encounter: null,
        result: resultFor({ ...nextEncounter, round: nextEncounter.round + 1 }, 'victory'),
      },
      { type: 'victory' },
    )
  }

  const target = chooseThreatTarget(nextCrew, state.activeCrew, encounter.round)
  if (target === null) {
    return commit(
      state,
      command,
      {
        phase: 'results',
        crew: nextCrew,
        encounter: null,
        result: resultFor({ ...nextEncounter, round: nextEncounter.round + 1 }, 'defeat'),
      },
      { type: 'defeat' },
    )
  }

  nextCrew = crewAfterDamage({ ...state, crew: nextCrew }, target, contract.enemyAttack)
  nextEncounter = { ...nextEncounter, round: nextEncounter.round + 1 }
  const livingAfterThreat = livingCrewIds(nextCrew, state.activeCrew)
  if (livingAfterThreat.length === 0) {
    return commit(
      state,
      command,
      {
        phase: 'results',
        crew: nextCrew,
        encounter: null,
        result: resultFor(nextEncounter, 'defeat'),
      },
      { type: 'defeat' },
    )
  }

  return commit(
    state,
    command,
    {
      crew: nextCrew,
      encounter: nextEncounter,
    },
    { type: 'action-resolved' },
  )
}

/** Applies one command without mutating the input state. Every accepted command is recorded. */
export function applyCommand(state: GameState, command: GameCommand): CommandResult {
  if (state.status === 'won' && command.type !== 'restart-campaign')
    return failure(state, 'ILLEGAL_PHASE')

  if (state.phase === 'start' && command.type === 'begin-onboarding') {
    return commit(
      state,
      command,
      { phase: 'onboarding' },
      { type: 'onboarding-started' },
    )
  }

  if (state.phase === 'onboarding' && command.type === 'complete-onboarding') {
    return commit(
      state,
      command,
      { phase: 'company' },
      { type: 'onboarding-completed' },
    )
  }

  if (state.phase === 'company' && command.type === 'select-contract') {
    if (!isContractId(command.contractId))
      return failure(state, 'INVALID_CONTRACT')
    if (state.completedContracts.includes(command.contractId))
      return failure(state, 'CONTRACT_COMPLETED')

    return commit(
      state,
      command,
      { selectedContract: command.contractId, phase: 'preparation', activeCrew: [] },
      { type: 'contract-selected' },
    )
  }

  if (state.phase === 'preparation' && command.type === 'leave-preparation') {
    return commit(
      state,
      command,
      { phase: 'company', selectedContract: null, activeCrew: [] },
      { type: 'preparation-left' },
    )
  }

  if (state.phase === 'preparation' && command.type === 'select-crew') {
    if (command.crew.length > 2)
      return failure(state, 'CREW_LIMIT')
    if (new Set(command.crew).size !== command.crew.length)
      return failure(state, 'DUPLICATE_CREW')
    if (command.crew.some(id => !isCrewId(id)))
      return failure(state, 'INVALID_CREW')
    if (command.crew.some(id => state.crew[id].health === 0))
      return failure(state, 'CREW_UNAVAILABLE')

    return commit(state, command, { activeCrew: [...command.crew] }, { type: 'crew-selected' })
  }

  if (state.phase === 'preparation' && command.type === 'buy-rations') {
    if (!isPositiveSafeInteger(command.amount))
      return failure(state, 'INVALID_AMOUNT')
    const cost = command.amount * 2
    if (!Number.isSafeInteger(cost) || state.resources.coin < cost)
      return failure(state, 'UNAFFORDABLE')

    return commit(
      state,
      command,
      {
        resources: {
          ...state.resources,
          coin: state.resources.coin - cost,
          rations: state.resources.rations + command.amount,
        },
      },
      { type: 'supplies-purchased' },
    )
  }

  if (state.phase === 'preparation' && command.type === 'launch-encounter') {
    if (state.selectedContract === null)
      return failure(state, 'INVALID_CONTRACT')
    if (state.activeCrew.length !== 2)
      return failure(state, 'CREW_REQUIRED')
    if (state.activeCrew.some(id => !isActiveCrew(state, id)))
      return failure(state, 'CREW_UNAVAILABLE')

    const contract = contractFor(state.selectedContract)
    if (state.resources.rations < contract.rationCost)
      return failure(state, 'UNAFFORDABLE')

    return commit(
      state,
      command,
      {
        phase: 'encounter',
        resources: {
          ...state.resources,
          rations: state.resources.rations - contract.rationCost,
        },
        encounter: {
          contractId: contract.id,
          enemyHealth: contract.enemyHealth,
          enemyMaxHealth: contract.enemyHealth,
          round: 0,
          healingCharges: state.activeCrew.some(id => hasRole(state, id, 'healer')) ? 1 : 0,
          bombCharges: state.activeCrew.some(id => hasRole(state, id, 'bomber')) ? 1 : 0,
        },
        result: null,
      },
      { type: 'encounter-started' },
    )
  }

  if (state.phase === 'encounter' && state.encounter !== null) {
    if (command.type === 'strike' || command.type === 'heal' || command.type === 'bomb') {
      if (!isCrewId(command.actor) || !isActiveCrew(state, command.actor))
        return failure(state, 'CREW_UNAVAILABLE')

      if (command.type === 'bomb') {
        if (!hasRole(state, command.actor, 'bomber') || state.encounter.bombCharges === 0)
          return failure(state, 'ACTION_UNAVAILABLE')
      }

      if (command.type === 'heal') {
        if (!hasRole(state, command.actor, 'healer') || state.encounter.healingCharges === 0)
          return failure(state, 'ACTION_UNAVAILABLE')
        if (!isCrewId(command.target) || !isActiveCrew(state, command.target))
          return failure(state, 'INVALID_TARGET')
        if (state.crew[command.target].health === state.crew[command.target].maxHealth)
          return failure(state, 'TARGET_FULL_HEALTH')
      }

      return resolveAction(state, command, state.crew, state.encounter)
    }
  }

  if (state.phase === 'results' && command.type === 'claim-reward') {
    if (state.result === null)
      return failure(state, 'NO_RESULT')
    if (state.result.outcome === 'defeat')
      return failure(state, 'NO_RESULT')
    if (state.result.rewardApplied)
      return failure(state, 'REWARD_ALREADY_APPLIED')

    const rewards = state.result.rewards
    return commit(
      state,
      command,
      {
        resources: {
          coin: state.resources.coin + rewards.coin,
          rations: state.resources.rations + rewards.rations,
          reputation: state.resources.reputation + rewards.reputation,
        },
        completedContracts: [...state.completedContracts, state.result.contractId],
        result: { ...state.result, rewardApplied: true },
      },
      { type: 'reward-applied' },
    )
  }

  if (state.phase === 'results' && command.type === 'continue-campaign') {
    if (state.result === null)
      return failure(state, 'NO_RESULT')
    if (state.result.outcome === 'victory' && !state.result.rewardApplied)
      return failure(state, 'REWARD_PENDING')
    if (state.result.outcome === 'defeat') {
      return commit(
        state,
        command,
        { phase: 'terminal', status: 'lost' },
        { type: 'defeat' },
      )
    }

    if (state.completedContracts.length === CONTRACT_IDS.length) {
      return commit(
        state,
        command,
        { phase: 'terminal', status: 'won' },
        { type: 'victory' },
      )
    }

    const recoveredCrew = Object.fromEntries(
      CREW_IDS.map((id) => {
        const member = state.crew[id]
        return [id, {
          ...member,
          health: Math.min(member.maxHealth, member.health + 2),
        }]
      }),
    ) as Record<CrewId, CrewState>

    return commit(
      state,
      command,
      {
        phase: 'company',
        status: 'active',
        selectedContract: null,
        activeCrew: [],
        encounter: null,
        result: null,
        crew: recoveredCrew,
      },
      { type: 'campaign-continued' },
    )
  }

  if (state.phase === 'terminal' && command.type === 'restart-campaign') {
    return {
      ok: true,
      state: createInitialState(),
      event: { type: 'campaign-restarted' },
    }
  }

  return failure(state, 'ILLEGAL_PHASE')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort()
  return actual.length === keys.length && actual.every((key, index) => key === [...keys].sort()[index])
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
}

function isResources(value: unknown): value is Resources {
  return isRecord(value)
    && hasExactKeys(value, ['coin', 'rations', 'reputation'])
    && isNonNegativeInteger(value.coin)
    && isNonNegativeInteger(value.rations)
    && isNonNegativeInteger(value.reputation)
}

function isPhase(value: unknown): value is GamePhase {
  return value === 'start' || value === 'onboarding' || value === 'company' || value === 'preparation' || value === 'encounter' || value === 'results' || value === 'terminal'
}

function isCommand(value: unknown): value is GameCommand {
  if (!isRecord(value) || typeof value.type !== 'string')
    return false

  switch (value.type) {
    case 'begin-onboarding':
    case 'complete-onboarding':
    case 'leave-preparation':
    case 'launch-encounter':
    case 'claim-reward':
    case 'continue-campaign':
    case 'restart-campaign':
      return hasExactKeys(value, ['type'])
    case 'select-contract':
      return hasExactKeys(value, ['type', 'contractId']) && isContractId(value.contractId)
    case 'select-crew':
      return hasExactKeys(value, ['type', 'crew']) && Array.isArray(value.crew) && value.crew.length <= 2 && new Set(value.crew).size === value.crew.length && value.crew.every(isCrewId)
    case 'buy-rations':
      return hasExactKeys(value, ['type', 'amount']) && isPositiveSafeInteger(value.amount)
    case 'strike':
    case 'bomb':
      return hasExactKeys(value, ['type', 'actor']) && isCrewId(value.actor)
    case 'heal':
      return hasExactKeys(value, ['type', 'actor', 'target']) && isCrewId(value.actor) && isCrewId(value.target)
    default:
      return false
  }
}

function equalNumberRecord(left: Resources, right: Resources): boolean {
  return left.coin === right.coin && left.rations === right.rations && left.reputation === right.reputation
}

function invalid(path: string): StateValidationResult {
  return { valid: false, code: 'INVALID_STATE', path }
}

/** Validates the complete serializable state before a save can be resumed. */
export function validateGameState(value: unknown): StateValidationResult {
  if (!isRecord(value))
    return invalid('state')
  if (!hasExactKeys(value, ['version', 'phase', 'status', 'resources', 'crew', 'activeCrew', 'selectedContract', 'completedContracts', 'encounter', 'result', 'history']))
    return invalid('state')
  if (value.version !== GAME_VERSION)
    return invalid('version')
  if (!isPhase(value.phase) || (value.status !== 'active' && value.status !== 'won' && value.status !== 'lost'))
    return invalid('phase')
  if (!isRecord(value.resources) || !hasExactKeys(value.resources, ['coin', 'rations', 'reputation']))
    return invalid('resources')
  if (!isNonNegativeInteger(value.resources.coin) || !isNonNegativeInteger(value.resources.rations) || !isNonNegativeInteger(value.resources.reputation))
    return invalid('resources')
  if (!isRecord(value.crew) || !hasExactKeys(value.crew, CREW_IDS))
    return invalid('crew')

  for (const id of CREW_IDS) {
    const member = value.crew[id]
    const definition = CREW_DEFINITIONS[id]
    if (!isRecord(member) || !hasExactKeys(member, ['id', 'name', 'roles', 'maxHealth', 'health']))
      return invalid(`crew.${id}`)
    if (member.id !== id || member.name !== definition.name || member.maxHealth !== definition.maxHealth)
      return invalid(`crew.${id}`)
    if (!Array.isArray(member.roles) || member.roles.length !== definition.roles.length || member.roles.some((role, index) => role !== definition.roles[index]))
      return invalid(`crew.${id}.roles`)
    if (!isNonNegativeInteger(member.health) || member.health > definition.maxHealth)
      return invalid(`crew.${id}.health`)
  }

  if (!Array.isArray(value.activeCrew) || value.activeCrew.some(id => !isCrewId(id)))
    return invalid('activeCrew')
  const activeCrew = value.activeCrew.filter(isCrewId)
  const crewRecord = value.crew as Record<CrewId, Record<string, unknown>>
  if (activeCrew.length > 2 || new Set(activeCrew).size !== activeCrew.length)
    return invalid('activeCrew')
  if (activeCrew.some(id => crewRecord[id].health === 0) && value.phase !== 'encounter' && value.phase !== 'results' && value.phase !== 'terminal')
    return invalid('activeCrew')
  if (!Array.isArray(value.completedContracts) || value.completedContracts.some(id => !isContractId(id)))
    return invalid('completedContracts')
  const completedContracts = value.completedContracts.filter(isContractId)
  if (new Set(completedContracts).size !== completedContracts.length)
    return invalid('completedContracts')
  if (value.selectedContract !== null && !isContractId(value.selectedContract))
    return invalid('selectedContract')
  if (value.selectedContract !== null && completedContracts.includes(value.selectedContract) && value.phase !== 'results' && value.phase !== 'terminal')
    return invalid('selectedContract')
  if (!Array.isArray(value.history))
    return invalid('history')

  for (const [index, entry] of value.history.entries()) {
    if (!isRecord(entry) || !hasExactKeys(entry, ['sequence', 'command', 'phaseBefore', 'phaseAfter']) || entry.sequence !== index || !isCommand(entry.command) || !isPhase(entry.phaseBefore) || !isPhase(entry.phaseAfter))
      return invalid(`history.${index}`)
  }

  if ((value.phase === 'start' || value.phase === 'onboarding' || value.phase === 'company') && (value.status !== 'active' || value.selectedContract !== null || activeCrew.length !== 0 || value.encounter !== null || value.result !== null))
    return invalid(value.phase)
  if (value.phase === 'preparation' && (value.status !== 'active' || value.selectedContract === null || activeCrew.length > 2 || value.encounter !== null || value.result !== null))
    return invalid('preparation')
  if (value.phase === 'preparation' && activeCrew.some(id => crewRecord[id].health === 0))
    return invalid('activeCrew')
  if (value.phase === 'encounter' && (value.status !== 'active' || value.selectedContract === null || activeCrew.length !== 2 || value.encounter === null || value.result !== null))
    return invalid('encounter')
  if (value.phase === 'encounter' && activeCrew.every(id => crewRecord[id].health === 0))
    return invalid('activeCrew')
  if (value.phase === 'results' && (value.status !== 'active' || value.selectedContract === null || activeCrew.length !== 2 || value.encounter !== null || value.result === null))
    return invalid('result')
  if (value.phase === 'terminal' && (value.selectedContract === null || value.encounter !== null || value.result === null))
    return invalid('result')
  if (value.phase === 'terminal' && value.status === 'active')
    return invalid('terminal')

  if (value.encounter !== null) {
    const encounter = value.encounter
    if (!isRecord(encounter) || !hasExactKeys(encounter, ['contractId', 'enemyHealth', 'enemyMaxHealth', 'round', 'healingCharges', 'bombCharges']) || !isContractId(encounter.contractId) || encounter.contractId !== value.selectedContract)
      return invalid('encounter')
    const contract = contractFor(encounter.contractId)
    if (!isNonNegativeInteger(encounter.enemyHealth) || encounter.enemyHealth === 0 || encounter.enemyHealth > contract.enemyHealth || encounter.enemyMaxHealth !== contract.enemyHealth || !isNonNegativeInteger(encounter.round) || !isNonNegativeInteger(encounter.healingCharges) || encounter.healingCharges > 1 || !isNonNegativeInteger(encounter.bombCharges) || encounter.bombCharges > 1)
      return invalid('encounter')
    if ((encounter.healingCharges === 1 && !activeCrew.some(id => CREW_DEFINITIONS[id].roles.includes('healer'))) || (encounter.bombCharges === 1 && !activeCrew.some(id => CREW_DEFINITIONS[id].roles.includes('bomber'))))
      return invalid('encounter')
  }

  if (value.result !== null) {
    const result = value.result
    if (!isRecord(result) || !hasExactKeys(result, ['outcome', 'contractId', 'rounds', 'rewards', 'rewardApplied']) || !isContractId(result.contractId) || result.contractId !== value.selectedContract || (result.outcome !== 'victory' && result.outcome !== 'defeat') || !isNonNegativeInteger(result.rounds) || typeof result.rewardApplied !== 'boolean' || !isResources(result.rewards))
      return invalid('result')
    const rewards = result.rewards
    if (!isResources(rewards) || !equalNumberRecord(rewards, contractFor(result.contractId).rewards) || (result.outcome === 'defeat' && result.rewardApplied))
      return invalid('result')
    if (result.rewardApplied !== completedContracts.includes(result.contractId))
      return invalid('result')
  }

  if (value.phase === 'terminal') {
    const terminalResult = value.result as CampaignResult
    if (value.status === 'won' && (terminalResult.outcome !== 'victory' || terminalResult.rewardApplied !== true || completedContracts.length !== CONTRACT_IDS.length))
      return invalid('terminal')
    if (value.status === 'lost' && terminalResult.outcome !== 'defeat')
      return invalid('terminal')
  }

  return { valid: true }
}
