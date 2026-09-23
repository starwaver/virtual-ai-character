import { describe, expect, it } from 'vitest'

import { mergeSnapshot } from './history'
import { agentName, normalizeRuntimeState } from './normalize'

const observedAt = '2026-09-23T01:00:00.000Z'

const fixture = {
  deploymentId: 'fixture',
  updatedAt: observedAt,
  tasks: [
    {
      id: '5',
      title: 'Build the board',
      url: 'https://github.com/starwaver/virtual-ai-character/issues/5',
      labels: ['symphony'],
      trackerState: 'open',
      status: 'doing',
      currentTask: 'Build the read-only board',
      progressSummary: 'The board is ready for review.',
      privateReasoning: 'This private reasoning must never reach the browser.',
      agents: [{ id: 'worker-1', role: 'worker', modelRoute: 'gpt-5.6-luna', progressSummary: 'The API boundary is ready.' }],
      counters: { turns: 3, retries: 0, inputTokens: 100, outputTokens: 40 },
      events: [{ id: 'event-1', type: 'implementation', publicSummary: 'The adapter is ready.', observedAt }],
    },
  ],
}

describe('normalizeRuntimeState', () => {
  // https://github.com/starwaver/virtual-ai-character/issues/5
  it('normalizes public fields and excludes private payloads', () => {
    const snapshot = normalizeRuntimeState(fixture, { deploymentId: 'fixture', observedAt })
    const task = snapshot.tasks[0]

    expect(task.key).toBe('tracker:5')
    expect(task.status).toBe('doing')
    expect(task.progressSummary).toBe('The board is ready for review.')
    expect(task.agents[0]?.name).toBe(agentName('worker-1', 'worker'))
    expect(task.counters.totalTokens).toBe(140)
    expect(task.events[0]?.summary).toBe('The adapter is ready.')
    expect(JSON.stringify(task)).not.toContain('private reasoning')
  })

  // https://github.com/starwaver/virtual-ai-character/issues/5
  it('applies lifecycle precedence for verification, blocking, retries, and review', () => {
    const state = {
      tasks: [
        { id: 'done', status: 'doing', verification: 'passed', finalized: true },
        { id: 'verified', status: 'verified' },
        { id: 'blocked', status: 'doing', blocked: true },
        { id: 'retrying', status: 'doing', retryScheduled: true },
        { id: 'qa', status: 'qa' },
        { id: 'completed', status: 'completed' },
        { id: 'attention', status: 'failed' },
      ],
    }
    const snapshot = normalizeRuntimeState(state, { deploymentId: 'fixture', observedAt })

    expect(snapshot.tasks.map(task => task.status)).toEqual(['done', 'done', 'blocked', 'retrying', 'qa', 'qa', 'attention'])
  })

  it('keeps logical agent names stable across refresh order', () => {
    const first = normalizeRuntimeState({ tasks: [{ id: '5', agents: [{ id: 'worker-1', role: 'worker' }] }] }, { deploymentId: 'fixture', observedAt })
    const second = normalizeRuntimeState({ tasks: [{ id: '6', agents: [{ id: 'worker-1', role: 'worker' }] }, { id: '5', agents: [{ id: 'worker-1', role: 'worker' }] }] }, { deploymentId: 'fixture', observedAt })

    expect(first.tasks[0]?.agents[0]?.name).toBe(second.tasks[1]?.agents[0]?.name)
  })
})

describe('mergeSnapshot', () => {
  // https://github.com/starwaver/virtual-ai-character/issues/5
  it('retains a task when it disappears from a later runtime snapshot', () => {
    const first = normalizeRuntimeState(fixture, { deploymentId: 'fixture', observedAt })
    const history = mergeSnapshot({
      schemaVersion: 1,
      deploymentId: 'fixture',
      lastSuccessfulSourceAt: null,
      tasks: [],
    }, first)
    const second = normalizeRuntimeState({ tasks: [] }, { deploymentId: 'fixture', observedAt: '2026-09-23T01:01:00.000Z' })
    const retained = mergeSnapshot(history, second)

    expect(retained.tasks).toHaveLength(1)
    expect(retained.tasks[0]?.missingFromSource).toBe(true)
    expect(retained.tasks[0]?.stale).toBe(true)
    expect(retained.tasks[0]?.status).toBe('doing')
  })
})
