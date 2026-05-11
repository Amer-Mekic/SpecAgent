import { useEffect, useMemo, useState } from 'react'
import './App.css'

function resolveApiBase() {
  const raw = import.meta.env.VITE_API_URL
  if (typeof raw === 'string' && raw.trim().length > 0) {
    return raw.replace(/\/$/, '')
  }
  return ''
}

export default function App() {
  const apiBase = useMemo(() => resolveApiBase(), [])
  const healthUrl = apiBase ? `${apiBase}/health` : '/health'
  const docsUrl = apiBase ? `${apiBase}/docs` : '/docs'
  const openApiUrl = apiBase ? `${apiBase}/openapi.json` : '/openapi.json'

  const [health, setHealth] = useState({ phase: 'loading' })

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(healthUrl)
        const body = res.ok ? await res.json().catch(() => ({})) : null
        if (!cancelled) {
          setHealth(
            res.ok
              ? { phase: 'ok', status: res.status, body }
              : { phase: 'error', status: res.status, detail: 'Unexpected response' },
          )
        }
      } catch (e) {
        if (!cancelled) {
          setHealth({
            phase: 'error',
            detail: e instanceof Error ? e.message : 'Request failed',
          })
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [healthUrl])

  return (
    <main className="spec-shell">
      <header className="spec-header">
        <h1>SpecAgent</h1>
        <p className="spec-lede">
          Frontend for the SpecAgent stack: document upload, requirement extraction, chat,
          traceability, and exports against the FastAPI backend.
        </p>
      </header>

      <section className="spec-panel" aria-live="polite">
        <h2>Backend</h2>
        {health.phase === 'loading' && <p className="spec-muted">Checking {healthUrl}…</p>}
        {health.phase === 'ok' && (
          <p>
            <span className="spec-badge spec-badge--ok">reachable</span>
            {health.body?.status != null && (
              <code className="spec-code"> status: {String(health.body.status)}</code>
            )}
          </p>
        )}
        {health.phase === 'error' && (
          <p>
            <span className="spec-badge spec-badge--err">unreachable</span>
            {health.detail != null && (
              <span className="spec-muted"> — {health.detail}</span>
            )}
            {health.status != null && (
              <span className="spec-muted"> (HTTP {health.status})</span>
            )}
          </p>
        )}
        <p className="spec-hint">
          Run the API (e.g. uvicorn on port 8000). With <code className="spec-code">npm run dev</code>,
          requests to <code className="spec-code">/api</code> and <code className="spec-code">/health</code>{' '}
          proxy to <code className="spec-code">{import.meta.env.DEV ? 'Vite → backend' : 'same origin'}</code>
          {import.meta.env.DEV && (
            <>
              {' '}
              (override backend URL: <code className="spec-code">VITE_BACKEND_URL</code> for the dev server
              proxy, or <code className="spec-code">VITE_API_URL</code> for direct fetches).
            </>
          )}
        </p>
      </section>

      <section className="spec-links">
        <a className="spec-link" href={docsUrl}>
          OpenAPI docs
        </a>
        <a className="spec-link spec-link--secondary" href={openApiUrl}>
          OpenAPI JSON
        </a>
      </section>
    </main>
  )
}
