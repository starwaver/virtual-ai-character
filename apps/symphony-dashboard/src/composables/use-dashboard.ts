import type { BoardColumn, DashboardSnapshot, TaskCard } from '../shared/task'

import { computed, onMounted, onUnmounted, readonly, shallowRef } from 'vue'

import { BOARD_COLUMNS } from '../shared/task'

export type DashboardConnectionState = 'loading' | 'ready' | 'empty' | 'stale' | 'error'

const INITIAL_DELAY_MS = 5_000
const MAX_DELAY_MS = 60_000

function isSnapshot(value: unknown): value is DashboardSnapshot {
  if (typeof value !== 'object' || value === null)
    return false
  const candidate = value as Partial<DashboardSnapshot>
  return Array.isArray(candidate.tasks)
    && typeof candidate.observedAt === 'string'
    && typeof candidate.sourceStatus === 'string'
}

function nextDelay(delay: number): number {
  return Math.min(delay * 2, MAX_DELAY_MS)
}

export function useDashboard() {
  const tasks = shallowRef<TaskCard[]>([])
  const loading = shallowRef(true)
  const errorCode = shallowRef<string | null>(null)
  const stale = shallowRef(false)
  const lastRefreshAt = shallowRef<string | null>(null)
  const nextPollDelay = shallowRef(INITIAL_DELAY_MS)
  const columns = computed(() => BOARD_COLUMNS.map(column => ({
    column,
    tasks: tasks.value.filter(task => task.status === column),
  })))
  const state = computed<DashboardConnectionState>(() => {
    if (loading.value && !tasks.value.length)
      return 'loading'
    if (errorCode.value)
      return stale.value ? 'stale' : 'error'
    return tasks.value.length ? 'ready' : 'empty'
  })

  let timer: ReturnType<typeof setTimeout> | undefined
  let controller: AbortController | undefined
  let refreshSequence = 0
  let disposed = false

  function scheduleRefresh(delay = nextPollDelay.value) {
    if (document.visibilityState === 'hidden')
      return
    if (timer)
      clearTimeout(timer)
    timer = setTimeout(() => void refresh(), delay)
  }

  async function refresh() {
    const sequence = ++refreshSequence
    controller?.abort()
    controller = new AbortController()
    loading.value = !tasks.value.length

    try {
      const response = await fetch('/api/dashboard/state', {
        cache: 'no-store',
        headers: { accept: 'application/json' },
        signal: controller.signal,
      })
      const payload: unknown = await response.json()
      if (!isSnapshot(payload))
        throw new Error('invalid_response')

      tasks.value = payload.tasks
      stale.value = payload.stale || payload.sourceStatus !== 'ok'
      errorCode.value = payload.sourceErrorCode
      lastRefreshAt.value = new Date().toISOString()
      nextPollDelay.value = INITIAL_DELAY_MS
    }
    catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError')
        return
      errorCode.value = 'unavailable'
      stale.value = true
      nextPollDelay.value = nextDelay(nextPollDelay.value)
    }
    finally {
      loading.value = false
      if (!disposed && sequence === refreshSequence)
        scheduleRefresh()
    }
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible')
      void refresh()
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibilityChange)
    void refresh()
  })

  onUnmounted(() => {
    disposed = true
    document.removeEventListener('visibilitychange', onVisibilityChange)
    controller?.abort()
    if (timer)
      clearTimeout(timer)
  })

  return {
    columns,
    errorCode: readonly(errorCode),
    lastRefreshAt: readonly(lastRefreshAt),
    loading: readonly(loading),
    refresh,
    stale: readonly(stale),
    state,
    tasks,
  }
}

export function statusLabelKey(column: BoardColumn): string {
  return `symphony.status.${column}`
}
