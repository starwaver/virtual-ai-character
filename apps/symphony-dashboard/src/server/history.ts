import type { Storage } from 'unstorage'

import type {
  DashboardHistory,
  DashboardSnapshot,
  TaskCard,
} from '../shared/task'

import fsLite from 'unstorage/drivers/fs-lite'

import { createStorage } from 'unstorage'

import {
  BOARD_COLUMNS,
  DASHBOARD_SCHEMA_VERSION,
  EMPTY_HISTORY,
} from '../shared/task'

const HISTORY_KEY = 'dashboard-history'

interface HistoryRepository {
  load: () => Promise<DashboardHistory>
  save: (history: DashboardHistory) => Promise<void>
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isTaskCard(value: unknown): value is TaskCard {
  if (!isRecord(value) || typeof value.key !== 'string' || !isRecord(value.issue) || !Array.isArray(value.agents) || !Array.isArray(value.events) || !Array.isArray(value.attempts))
    return false

  return typeof value.issue.identifier === 'string'
    && typeof value.issue.title === 'string'
    && typeof value.status === 'string'
    && (BOARD_COLUMNS as readonly string[]).includes(value.status)
}

function readHistory(value: unknown): DashboardHistory {
  if (!isRecord(value) || !Array.isArray(value.tasks))
    return { ...EMPTY_HISTORY, tasks: [] }

  return {
    schemaVersion: value.schemaVersion === DASHBOARD_SCHEMA_VERSION ? DASHBOARD_SCHEMA_VERSION : DASHBOARD_SCHEMA_VERSION,
    deploymentId: typeof value.deploymentId === 'string' ? value.deploymentId : 'unknown',
    lastSuccessfulSourceAt: typeof value.lastSuccessfulSourceAt === 'string' ? value.lastSuccessfulSourceAt : null,
    tasks: value.tasks.filter(isTaskCard),
  }
}

function mergeTask(previous: TaskCard | undefined, current: TaskCard): TaskCard {
  if (!previous)
    return current

  const attempts = [...current.attempts, ...previous.attempts]
    .filter((attempt, index, all) => all.findIndex(candidate => candidate.id === attempt.id) === index)
    .slice(0, 30)
  const events = [...current.events, ...previous.events]
    .filter((event, index, all) => all.findIndex(candidate => candidate.id === event.id) === index)
    .sort((left, right) => Date.parse(right.observedAt) - Date.parse(left.observedAt))
    .slice(0, 40)

  return {
    ...current,
    attempts,
    events,
  }
}

/**
 * Merges one source snapshot into retained task history.
 *
 * A missing task stays visible and becomes stale. The dashboard never treats
 * disappearance from a transient source snapshot as verification.
 */
export function mergeSnapshot(history: DashboardHistory, snapshot: DashboardSnapshot): DashboardHistory {
  const currentByKey = new Map(snapshot.tasks.map(task => [task.key, task]))
  const taskKeys = new Set([...history.tasks.map(task => task.key), ...snapshot.tasks.map(task => task.key)])
  const tasks = [...taskKeys].map((key) => {
    const current = currentByKey.get(key)
    const previous = history.tasks.find(task => task.key === key)

    if (current)
      return mergeTask(previous, current)
    if (!previous)
      return undefined

    return {
      ...previous,
      stale: true,
      missingFromSource: true,
      observedAt: snapshot.observedAt,
    }
  }).filter((task): task is TaskCard => task !== undefined)

  return {
    schemaVersion: DASHBOARD_SCHEMA_VERSION,
    deploymentId: snapshot.deploymentId,
    lastSuccessfulSourceAt: snapshot.observedAt,
    tasks,
  }
}

export function historySnapshot(history: DashboardHistory, observedAt: string, sourceStatus: DashboardSnapshot['sourceStatus'], sourceErrorCode: string | null): DashboardSnapshot {
  return {
    schemaVersion: DASHBOARD_SCHEMA_VERSION,
    deploymentId: history.deploymentId,
    observedAt,
    sourceUpdatedAt: history.lastSuccessfulSourceAt,
    sourceStatus,
    sourceErrorCode,
    stale: sourceStatus !== 'ok' || history.tasks.some(task => task.stale),
    tasks: history.tasks,
  }
}

export function createHistoryRepository(options: { basePath: string, storage?: Storage }): HistoryRepository {
  const storage = options.storage ?? createStorage({
    driver: fsLite({ base: options.basePath }),
  })

  return {
    async load() {
      const serialized = await storage.getItem<string>(HISTORY_KEY)
      if (!serialized)
        return { ...EMPTY_HISTORY, tasks: [] }

      try {
        return readHistory(JSON.parse(serialized))
      }
      catch {
        return { ...EMPTY_HISTORY, tasks: [] }
      }
    },
    async save(history) {
      await storage.setItem(HISTORY_KEY, JSON.stringify(history))
    },
  }
}

export type { HistoryRepository }
