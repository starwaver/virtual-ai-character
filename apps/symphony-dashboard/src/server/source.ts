export interface RuntimeSource {
  readState: () => Promise<unknown>
  readTask: (taskKey: string) => Promise<unknown>
}

export type RuntimeSourceErrorCode = 'unavailable' | 'timeout' | 'unsupported' | 'invalid_url'

export class RuntimeSourceError extends Error {
  constructor(readonly code: RuntimeSourceErrorCode) {
    super(code)
    this.name = 'RuntimeSourceError'
  }
}

interface RuntimeSourceOptions {
  baseUrl: string
  fetchImpl?: typeof fetch
  timeoutMs?: number
}

function createEndpoint(baseUrl: string, path: string): URL {
  try {
    const base = new URL(baseUrl)
    if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password)
      throw new RuntimeSourceError('invalid_url')

    return new URL(path, base)
  }
  catch (error) {
    if (error instanceof RuntimeSourceError)
      throw error
    throw new RuntimeSourceError('invalid_url')
  }
}

async function fetchJson(url: URL, fetchImpl: typeof fetch, timeoutMs: number): Promise<unknown> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetchImpl(url, {
      method: 'GET',
      headers: { accept: 'application/json' },
      redirect: 'error',
      signal: controller.signal,
    })

    if (response.status === 404)
      throw new RuntimeSourceError('unsupported')
    if (!response.ok)
      throw new RuntimeSourceError('unavailable')

    return await response.json() as unknown
  }
  catch (error) {
    if (error instanceof RuntimeSourceError)
      throw error
    if (error instanceof Error && error.name === 'AbortError')
      throw new RuntimeSourceError('timeout')
    throw new RuntimeSourceError('unavailable')
  }
  finally {
    clearTimeout(timeout)
  }
}

export function createRuntimeSource(options: RuntimeSourceOptions): RuntimeSource {
  const fetchImpl = options.fetchImpl ?? fetch
  const timeoutMs = options.timeoutMs ?? 10_000

  return {
    readState() {
      return fetchJson(createEndpoint(options.baseUrl, '/api/v1/state'), fetchImpl, timeoutMs)
    },
    readTask(taskKey) {
      const taskId = taskKey.includes(':') ? taskKey.slice(taskKey.lastIndexOf(':') + 1) : taskKey
      return fetchJson(createEndpoint(options.baseUrl, `/api/v1/tasks/${encodeURIComponent(taskId)}`), fetchImpl, timeoutMs)
    },
  }
}
