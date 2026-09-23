export const DASHBOARD_SCHEMA_VERSION = 1

export const BOARD_COLUMNS = [
  'todo',
  'doing',
  'qa',
  'blocked',
  'retrying',
  'done',
  'attention',
] as const

export type BoardColumn = typeof BOARD_COLUMNS[number]

export interface TaskIssue {
  identifier: string
  title: string
  url: string | null
  labels: string[]
  trackerState: string | null
}

export type AgentRole = 'worker' | 'reviewer' | 'orchestrator'

export interface AgentSummary {
  id: string
  name: string
  role: AgentRole
  modelRoute: string | null
  currentTask: string | null
  progressSummary: string | null
}

export interface TaskEvent {
  id: string
  type: string
  summary: string | null
  observedAt: string
}

export interface TaskCounters {
  turns: number | null
  retries: number | null
  runtimeMs: number | null
  inputTokens: number | null
  outputTokens: number | null
  totalTokens: number | null
}

export interface TaskAttempt {
  id: string
  status: BoardColumn
  startedAt: string | null
  updatedAt: string | null
  agents: AgentSummary[]
  counters: TaskCounters
  branch: string | null
  workspace: string | null
  pullRequestUrl: string | null
  reviewerDecision: string | null
  errorCode: string | null
}

export interface TaskCard {
  key: string
  issue: TaskIssue
  status: BoardColumn
  sourceUpdatedAt: string | null
  observedAt: string
  stale: boolean
  missingFromSource: boolean
  currentTask: string | null
  latestEvent: TaskEvent | null
  progressSummary: string | null
  agents: AgentSummary[]
  counters: TaskCounters
  startedAt: string | null
  lastUpdatedAt: string | null
  branch: string | null
  workspace: string | null
  pullRequestUrl: string | null
  reviewerDecision: string | null
  errorCode: string | null
  attempts: TaskAttempt[]
  events: TaskEvent[]
}

export interface DashboardSnapshot {
  schemaVersion: number
  deploymentId: string
  observedAt: string
  sourceUpdatedAt: string | null
  sourceStatus: 'ok' | 'error' | 'unsupported'
  sourceErrorCode: string | null
  stale: boolean
  tasks: TaskCard[]
}

export interface DashboardHistory {
  schemaVersion: number
  deploymentId: string
  lastSuccessfulSourceAt: string | null
  tasks: TaskCard[]
}

export const EMPTY_COUNTERS: TaskCounters = Object.freeze({
  turns: null,
  retries: null,
  runtimeMs: null,
  inputTokens: null,
  outputTokens: null,
  totalTokens: null,
})

export const EMPTY_HISTORY: DashboardHistory = Object.freeze({
  schemaVersion: DASHBOARD_SCHEMA_VERSION,
  deploymentId: 'unknown',
  lastSuccessfulSourceAt: null,
  tasks: [],
})
