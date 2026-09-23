import type {
  AgentRole,
  AgentSummary,
  BoardColumn,
  DashboardSnapshot,
  TaskAttempt,
  TaskCard,
  TaskCounters,
  TaskEvent,
} from '../shared/task'

import {
  DASHBOARD_SCHEMA_VERSION,
  EMPTY_COUNTERS,
} from '../shared/task'

type RecordValue = Record<string, unknown>

export interface NormalizeOptions {
  deploymentId: string
  observedAt?: string
  allowedLinkHosts?: readonly string[]
}

export class InvalidRuntimeStateError extends Error {
  readonly code = 'invalid_state'

  constructor() {
    super('The runtime state does not match the public dashboard contract.')
    this.name = 'InvalidRuntimeStateError'
  }
}

const DEFAULT_LINK_HOSTS = ['github.com']
const ADJECTIVES = ['Amber', 'Brisk', 'Clever', 'Copper', 'Daring', 'Fuzzy', 'Mellow', 'Pixel', 'Sunny', 'Velvet']
const ANIMALS = ['badger', 'beaver', 'bison', 'otter', 'panda', 'quokka', 'raccoon', 'seal', 'tiger', 'wombat']
const PUBLIC_TEXT_LIMIT = 240
const SECRET_MARKER = /sk-[a-z0-9]|gh[pousr]_[a-z0-9]|bearer\s|private\s+key|password|api[_ -]?key/i

function asRecord(value: unknown): RecordValue | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as RecordValue
    : null
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function getRecord(value: RecordValue, key: string): RecordValue | null {
  return asRecord(value[key])
}

function getString(value: RecordValue, key: string): string | null {
  return typeof value[key] === 'string' && value[key].trim() ? value[key].trim() : null
}

function getNumber(value: RecordValue, key: string): number | null {
  return typeof value[key] === 'number' && Number.isFinite(value[key]) && value[key] >= 0
    ? value[key]
    : null
}

function getTimestamp(value: RecordValue, ...keys: string[]): string | null {
  for (const key of keys) {
    const candidate = getString(value, key)
    if (candidate && Number.isFinite(Date.parse(candidate)))
      return candidate
  }
  return null
}

function publicText(value: unknown): string | null {
  if (typeof value !== 'string')
    return null

  const text = [...value].filter((character) => {
    const code = character.codePointAt(0) ?? 0
    return code >= 32 && code !== 127
  }).join('').trim()
  if (!text || text.length > PUBLIC_TEXT_LIMIT || SECRET_MARKER.test(text))
    return null

  return text
}

function publicIdentifier(value: unknown, limit = 96): string | null {
  const text = publicText(value)
  return text && text.length <= limit ? text : null
}

function safeCode(value: unknown): string | null {
  const code = publicIdentifier(value, 64)
  return code && /^[\w.:-]+$/.test(code) ? code : null
}

function safeLink(value: unknown, allowedHosts: readonly string[]): string | null {
  if (typeof value !== 'string')
    return null

  try {
    const url = new URL(value)
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password)
      return null
    if (!allowedHosts.includes(url.hostname) || [...url.searchParams.values()].some(item => SECRET_MARKER.test(item)))
      return null
    return url.toString()
  }
  catch {
    return null
  }
}

function stableHash(value: string): string {
  let hash = 2166136261
  for (const character of value) {
    hash ^= character.codePointAt(0) ?? 0
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(16).padStart(8, '0')
}

/**
 * Returns a stable display name for one logical agent assignment.
 *
 * @example
 * agentName('worker-1', 'worker')
 * // => 'Clever otter · 7e3a5a2c'
 */
export function agentName(identity: string, role: AgentRole): string {
  const hash = stableHash(`${role}:${identity}`)
  const number = Number.parseInt(hash.slice(0, 8), 16)
  return `${ADJECTIVES[number % ADJECTIVES.length]} ${ANIMALS[(number >>> 4) % ANIMALS.length]} · ${hash.slice(0, 8)}`
}

function normalizeRole(value: unknown, fallback: AgentRole): AgentRole {
  return value === 'worker' || value === 'reviewer' || value === 'orchestrator' ? value : fallback
}

function normalizeCounters(value: RecordValue | null): TaskCounters {
  if (!value)
    return { ...EMPTY_COUNTERS }

  const inputTokens = getNumber(value, 'inputTokens') ?? getNumber(value, 'input_tokens')
  const outputTokens = getNumber(value, 'outputTokens') ?? getNumber(value, 'output_tokens')
  const totalTokens = getNumber(value, 'totalTokens') ?? getNumber(value, 'total_tokens')

  return {
    turns: getNumber(value, 'turns') ?? getNumber(value, 'turnCount'),
    retries: getNumber(value, 'retries') ?? getNumber(value, 'retryCount'),
    runtimeMs: getNumber(value, 'runtimeMs') ?? getNumber(value, 'runtime_ms'),
    inputTokens,
    outputTokens,
    totalTokens: totalTokens ?? (inputTokens !== null && outputTokens !== null ? inputTokens + outputTokens : null),
  }
}

function normalizeAgent(value: unknown, taskKey: string, fallbackRole: AgentRole): AgentSummary | null {
  const agent = asRecord(value)
  if (!agent)
    return null

  const role = normalizeRole(agent.role, fallbackRole)
  const id = publicIdentifier(agent.id) ?? publicIdentifier(agent.identity) ?? `${taskKey}:${role}`
  return {
    id,
    name: agentName(id, role),
    role,
    modelRoute: getString(agent, 'modelRoute') ?? getString(agent, 'model_route'),
    currentTask: publicText(agent.currentTask ?? agent.current_task),
    progressSummary: publicText(agent.progressSummary ?? agent.progress_summary),
  }
}

function normalizeAgents(value: unknown, taskKey: string): AgentSummary[] {
  return asArray(value)
    .map(item => normalizeAgent(item, taskKey, 'worker'))
    .filter((agent): agent is AgentSummary => agent !== null)
}

function normalizeEvent(value: unknown, taskKey: string, index: number): TaskEvent | null {
  const event = asRecord(value)
  if (!event)
    return null

  const type = publicIdentifier(event.type, 64) ?? publicIdentifier(event.name, 64)
  const observedAt = getTimestamp(event, 'observedAt', 'timestamp', 'createdAt')
  if (!type || !observedAt)
    return null

  const summary = publicText(event.publicSummary ?? event.public_summary)
  const id = publicIdentifier(event.id) ?? `${taskKey}:${type}:${observedAt}:${index}`
  return { id, type, summary, observedAt }
}

function normalizeEvents(value: unknown, taskKey: string): TaskEvent[] {
  return asArray(value)
    .map((item, index) => normalizeEvent(item, taskKey, index))
    .filter((event): event is TaskEvent => event !== null)
    .sort((left, right) => Date.parse(right.observedAt) - Date.parse(left.observedAt))
    .slice(0, 40)
}

function statusFrom(value: RecordValue): BoardColumn {
  const state = (getString(value, 'status') ?? getString(value, 'phase') ?? getString(value, 'state') ?? '').toLowerCase()
  const verification = (getString(value, 'verification') ?? getString(value, 'verificationStatus') ?? '').toLowerCase()
  const reviewer = (getString(value, 'reviewerDecision') ?? '').toLowerCase()
  const finalized = value.finalized === true || value.finalizedAt !== undefined

  const verified = verification === 'passed' || verification === 'verified' || state === 'verified'

  if (verified && (finalized || state === 'verified'))
    return 'done'
  if (state === 'blocked' || value.blocked === true)
    return 'blocked'
  if (state === 'retrying' || state === 'retry' || value.retryScheduled === true)
    return 'retrying'
  if (state === 'doing' || state === 'working' || state === 'reviewing' || value.active === true)
    return 'doing'
  if (state === 'qa' || state === 'review' || state === 'needs-review' || state === 'needs_review' || state === 'awaiting-review' || state === 'awaiting_review' || state === 'completed' || state === 'complete' || reviewer === 'pending')
    return 'qa'
  if (state === 'failed' || state === 'cancelled' || state === 'canceled')
    return 'attention'
  return state === 'done' ? 'qa' : 'todo'
}

function normalizeAttempt(value: RecordValue, taskKey: string, fallbackStatus: BoardColumn, allowedLinkHosts: readonly string[]): TaskAttempt {
  const id = getString(value, 'id') ?? getString(value, 'attemptId') ?? `${taskKey}:attempt-1`
  const status = statusFrom(value) === 'todo' && fallbackStatus !== 'todo' ? fallbackStatus : statusFrom(value)
  const agents = normalizeAgents(value.agents, taskKey)
  const counters = normalizeCounters(getRecord(value, 'counters') ?? value)
  const pullRequestUrl = safeLink(value.pullRequestUrl ?? value.pull_request_url, allowedLinkHosts)

  return {
    id,
    status,
    startedAt: getTimestamp(value, 'startedAt', 'started_at'),
    updatedAt: getTimestamp(value, 'updatedAt', 'updated_at'),
    agents,
    counters,
    branch: getString(value, 'branch'),
    workspace: publicText(value.workspace ?? value.workspaceLabel),
    pullRequestUrl,
    reviewerDecision: publicText(value.reviewerDecision ?? value.reviewer_decision),
    errorCode: safeCode(value.errorCode) ?? safeCode(value.error_code),
  }
}

function taskIssue(value: RecordValue, allowedLinkHosts: readonly string[]): { key: string, issue: TaskCard['issue'] } | null {
  const issue = getRecord(value, 'issue') ?? value
  const identifier = publicIdentifier(issue.identifier) ?? publicIdentifier(issue.id) ?? publicIdentifier(issue.number)
  if (!identifier)
    return null

  const repository = publicIdentifier(issue.repository) ?? publicIdentifier(issue.repo) ?? 'tracker'
  return {
    key: `${repository}:${identifier}`,
    issue: {
      identifier,
      title: publicText(issue.title) ?? `Task ${identifier}`,
      url: safeLink(issue.url ?? issue.htmlUrl, allowedLinkHosts),
      labels: asArray(issue.labels)
        .map(label => publicText(label))
        .filter((label): label is string => label !== null)
        .slice(0, 20),
      trackerState: publicText(issue.trackerState) ?? publicText(issue.state),
    },
  }
}

function normalizeTask(value: unknown, observedAt: string, allowedLinkHosts: readonly string[]): TaskCard | null {
  const task = asRecord(value)
  if (!task)
    return null

  const identity = taskIssue(task, allowedLinkHosts)
  if (!identity)
    return null

  const status = statusFrom(task)
  const events = normalizeEvents(task.events, identity.key)
  const agents = normalizeAgents(task.agents, identity.key)
  const counters = normalizeCounters(getRecord(task, 'counters') ?? task)
  const attemptValues = asArray(task.attempts).map(asRecord).filter((attempt): attempt is RecordValue => attempt !== null)
  const attempts = (attemptValues.length ? attemptValues : [task])
    .map(attempt => normalizeAttempt(attempt, identity.key, status, allowedLinkHosts))
  const current = attempts[0]
  const latestEvent = events[0] ?? null

  return {
    key: identity.key,
    issue: identity.issue,
    status,
    sourceUpdatedAt: getTimestamp(task, 'updatedAt', 'updated_at', 'lastUpdateAt'),
    observedAt,
    stale: false,
    missingFromSource: false,
    currentTask: publicText(task.currentTask ?? task.current_task),
    latestEvent,
    progressSummary: publicText(task.progressSummary ?? task.progress_summary),
    agents: agents.length ? agents : current.agents,
    counters,
    startedAt: getTimestamp(task, 'startedAt', 'started_at') ?? current.startedAt,
    lastUpdatedAt: getTimestamp(task, 'lastUpdatedAt', 'last_updated_at', 'updatedAt') ?? current.updatedAt,
    branch: publicText(task.branch) ?? current.branch,
    workspace: publicText(task.workspace ?? task.workspaceLabel) ?? current.workspace,
    pullRequestUrl: safeLink(task.pullRequestUrl ?? task.pull_request_url, allowedLinkHosts) ?? current.pullRequestUrl,
    reviewerDecision: publicText(task.reviewerDecision ?? task.reviewer_decision) ?? current.reviewerDecision,
    errorCode: safeCode(task.errorCode) ?? safeCode(task.error_code) ?? current.errorCode,
    attempts,
    events,
  }
}

/**
 * Normalizes a runtime snapshot into the dashboard's allowlisted public shape.
 *
 * @example
 * normalizeRuntimeState({ tasks: [{ id: '5', title: 'Ship it', status: 'doing' }] }, options)
 * // => { tasks: [{ key: 'tracker:5', status: 'doing', ... }] }
 */
export function normalizeRuntimeState(value: unknown, options: NormalizeOptions): DashboardSnapshot {
  const source = asRecord(value)
  if (!source)
    throw new InvalidRuntimeStateError()

  const rawTasks = source.tasks ?? source.items
  if (!Array.isArray(rawTasks))
    throw new InvalidRuntimeStateError()

  const observedAt = options.observedAt ?? new Date().toISOString()
  const allowedLinkHosts = options.allowedLinkHosts ?? DEFAULT_LINK_HOSTS
  const tasks = rawTasks
    .map(task => normalizeTask(task, observedAt, allowedLinkHosts))
    .filter((task): task is TaskCard => task !== null)

  return {
    schemaVersion: DASHBOARD_SCHEMA_VERSION,
    deploymentId: options.deploymentId,
    observedAt,
    sourceUpdatedAt: getTimestamp(source, 'updatedAt', 'updated_at', 'lastUpdateAt'),
    sourceStatus: 'ok',
    sourceErrorCode: null,
    stale: false,
    tasks,
  }
}
