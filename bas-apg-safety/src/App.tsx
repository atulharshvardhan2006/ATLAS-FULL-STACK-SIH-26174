import React, { useState, useEffect, useRef } from 'react'

interface CrewMember {
  crew_id: number
  status: 'NOMINAL' | 'WARNING' | 'CRITICAL'
  centroid: [number, number]
  bbox: [number, number, number, number]
  velocity_px: number
  frames_immobile: number
  zone_entry_time: number | null
}

interface CrewSafety {
  active: boolean
  crew: CrewMember[]
}

const App: React.FC = () => {
  const [crew, setCrew] = useState<CrewMember[]>([])
  const [connected, setConnected] = useState(false)
  const [fps, setFps] = useState(0)
  const [lastUpdate, setLastUpdate] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>()

  // ── WebSocket connection ─────────────────────────────────
  useEffect(() => {
    const connect = () => {
      const sessionId = `safety-${Date.now()}`
      const ws = new WebSocket(`ws://localhost:8000/ws/telemetry/${sessionId}`)

      ws.onopen = () => {
        setConnected(true)
        console.log('[SAFETY] WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          const safety: CrewSafety = data.crew_safety
          if (safety && safety.crew) {
            setCrew(safety.crew)
          }
          setFps(data.fps ?? 0)
          setLastUpdate(data.timestamp ?? '')
        } catch {}
      }

      ws.onclose = () => {
        setConnected(false)
        reconnectRef.current = setTimeout(connect, 2000)
      }

      ws.onerror = () => ws.close()
      wsRef.current = ws
    }

    connect()
    return () => {
      wsRef.current?.close()
      clearTimeout(reconnectRef.current)
    }
  }, [])

  // ── Derived stats ────────────────────────────────────────
  const totalCrew = crew.length
  const nominalCount = crew.filter(c => c.status === 'NOMINAL').length
  const warningCount = crew.filter(c => c.status === 'WARNING').length
  const criticalCount = crew.filter(c => c.status === 'CRITICAL').length
  const hasCritical = criticalCount > 0

  return (
    <div className="safety-app">
      {/* ── HEADER ──────────────────────────────────────── */}
      <header className="header">
        <div className="header-left">
          <div className="header-title">
            <span>△ TLAS</span> &nbsp; crew safety monitor
          </div>
        </div>
        <div className={`header-badge ${hasCritical ? 'badge-alert' : 'badge-active'}`}>
          {hasCritical
            ? '⚠ CREW SAFETY ALERT'
            : connected
              ? '● OVERWATCH ACTIVE'
              : '○ DISCONNECTED'}
        </div>
      </header>

      {/* ── MAIN GRID ───────────────────────────────────── */}
      <div className="main-grid">
        {/* ── LEFT: Video Feed ──────────────────────────── */}
        <div className="video-section">
          <div className="video-label">optical sensor trunk [ overwatch ]</div>

          <div className="video-container">
            <img
              src="http://localhost:8000/video_feed"
              alt="Live Feed"
            />
            <div className="video-overlay-tag">
              CREW TRACKING ACTIVE
            </div>
          </div>

          {/* ── Stats Bar ───────────────────────────────── */}
          <div className="stats-bar">
            <div className="stat-card">
              <div className="stat-label">Total Crew</div>
              <div className="stat-value blue">{totalCrew}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Nominal</div>
              <div className="stat-value green">{nominalCount}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">In Zone</div>
              <div className="stat-value yellow">{warningCount}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Critical</div>
              <div className="stat-value red">{criticalCount}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Feed FPS</div>
              <div className="stat-value blue">{fps.toFixed(0)}</div>
            </div>
          </div>
        </div>

        {/* ── RIGHT: Crew Roster ────────────────────────── */}
        <div className="roster-panel">
          <div className="roster-title">crew telemetry roster</div>

          {crew.length === 0 ? (
            <div className="no-crew">
              <div className="no-crew-icon">👤</div>
              <div className="no-crew-text">No crew detected</div>
            </div>
          ) : (
            crew.map((member) => (
              <CrewCard key={member.crew_id} member={member} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}

// ── CREW CARD COMPONENT ──────────────────────────────────────

const CrewCard: React.FC<{ member: CrewMember }> = ({ member }) => {
  const statusClass = member.status.toLowerCase()
  const badgeClass = `badge-${statusClass}`

  const zoneTime = member.zone_entry_time
    ? `${((Date.now() / 1000) - member.zone_entry_time).toFixed(0)}s`
    : '—'

  return (
    <div className={`crew-card ${statusClass}`}>
      <div className="crew-header">
        <div className="crew-id">Crew {member.crew_id}</div>
        <div className={`crew-status-badge ${badgeClass}`}>{member.status}</div>
      </div>

      <div className="crew-metrics">
        <div className="metric">
          <div className="metric-label">Velocity</div>
          <div className="metric-value">{member.velocity_px.toFixed(1)} px/s</div>
        </div>
        <div className="metric">
          <div className="metric-label">Position</div>
          <div className="metric-value">
            {member.centroid[0].toFixed(0)}, {member.centroid[1].toFixed(0)}
          </div>
        </div>
        <div className="metric">
          <div className="metric-label">Zone Time</div>
          <div className="metric-value">{zoneTime}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Immobile Frames</div>
          <div className="metric-value">{member.frames_immobile}</div>
        </div>
      </div>
    </div>
  )
}

export default App
