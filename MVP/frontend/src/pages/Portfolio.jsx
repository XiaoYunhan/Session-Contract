import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'
import { WebSocketClient } from '../lib/websocket'

export default function Portfolio() {
  const { sessionId } = useParams()
  const [session, setSession] = useState(null)
  const [participants, setParticipants] = useState([])
  const [allocations, setAllocations] = useState({})
  const [prices, setPrices] = useState({})
  const [settlement, setSettlement] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAddParticipant, setShowAddParticipant] = useState(false)
  const [participantForm, setParticipantForm] = useState({ participant_id: '', name: '' })
  const [ws, setWs] = useState(null)

  useEffect(() => {
    loadData()

    // Setup WebSocket
    const wsClient = new WebSocketClient(sessionId)
    wsClient.connect()

    wsClient.on('price_update', (msg) => {
      setPrices(msg.prices)
    })

    wsClient.on('allocation_update', (msg) => {
      setAllocations(msg.allocations)
    })

    wsClient.on('session_status', (msg) => {
      if (session) {
        setSession({ ...session, status: msg.status })
      }
    })

    setWs(wsClient)

    return () => {
      wsClient.disconnect()
    }
  }, [sessionId])

  async function loadData() {
    try {
      setLoading(true)
      const [sessionData, participantsData, allocationsData] = await Promise.all([
        api.getSession(sessionId),
        api.getParticipants(sessionId),
        api.getAllocations(sessionId)
      ])
      setSession(sessionData)
      setParticipants(participantsData)
      setAllocations(allocationsData.allocations || {})

      // Try to get prices and settlement
      try {
        const pricesData = await api.getLatestPrices(sessionId)
        setPrices(pricesData.prices || {})
      } catch (err) {
        // No prices yet
      }

      if (sessionData.status === 'settled') {
        try {
          const settlementData = await api.getSettlement(sessionId)
          setSettlement(settlementData)
        } catch (err) {
          // No settlement yet
        }
      }

      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleAddParticipant(e) {
    e.preventDefault()
    try {
      await api.addParticipant(sessionId, participantForm)
      setShowAddParticipant(false)
      setParticipantForm({ participant_id: '', name: '' })
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleAssignAllocations() {
    try {
      await api.assignAllocations(sessionId, {})
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleSettle() {
    if (!window.confirm('Are you sure you want to settle this session?')) {
      return
    }
    try {
      const settlementData = await api.settleSession(sessionId)
      setSettlement(settlementData)
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  function calculateValue(allocation) {
    if (!allocation || Object.keys(prices).length === 0) return 0
    return Object.entries(allocation).reduce((sum, [leg, qty]) => {
      return sum + (qty * (prices[leg] || 0))
    }, 0)
  }

  if (loading) {
    return <div className="container"><div className="loading">Loading portfolio...</div></div>
  }

  if (!session) {
    return <div className="container"><div className="error">Session not found</div></div>
  }

  return (
    <div className="container">
      <div className="header terminal-glow">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>PORTFOLIO • {session.session_id.toUpperCase()}</h1>
            <span className={`status-badge status-${session.status}`}>
              {session.status.toUpperCase()}
            </span>
          </div>
          <Link to="/"><button className="secondary">DASHBOARD</button></Link>
        </div>
      </div>

      {error && <div className="card"><div className="error">{error}</div></div>}

      <div className="grid grid-2">
        <div className="card">
          <h2>Session Info</h2>
          <table>
            <tbody>
              <tr><td><strong>Legs:</strong></td><td>{session.legs.join(', ')}</td></tr>
              <tr><td><strong>Basket:</strong></td><td>{session.q.join(', ')}</td></tr>
              <tr><td><strong>Mode:</strong></td><td>{session.start_mode} → {session.end_mode}</td></tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <h2>MARKET DATA</h2>
          {Object.keys(prices).length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 40, border: '1px dashed var(--border)', borderRadius: 'var(--radius)' }}>
              <p>No price data. Start oracle to stream live prices.</p>
            </div>
          ) : (
            <div className="grid grid-4">
              {Object.entries(prices).map(([leg, price]) => (
                <div key={leg} className="price-card price-update">
                  <div className="ticker">{leg}</div>
                  <div className="price-value">${price.toFixed(2)}</div>
                  <div className="price-change" style={{ color: 'var(--terminal-green)' }}>
                    LIVE
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2>PARTICIPANTS & ALLOCATIONS</h2>
          <div style={{ display: 'flex', gap: 10 }}>
            {participants.length > 0 && Object.keys(allocations).length === 0 && (
              <button className="success" onClick={handleAssignAllocations}>ASSIGN ALLOCATIONS</button>
            )}
            <button className={showAddParticipant ? 'secondary' : 'primary'} onClick={() => setShowAddParticipant(!showAddParticipant)}>
              {showAddParticipant ? 'CANCEL' : 'ADD PARTICIPANT'}
            </button>
          </div>
        </div>

        {showAddParticipant && (
          <form onSubmit={handleAddParticipant} style={{ marginBottom: 20, padding: 20, background: '#f8f9fa', borderRadius: 8 }}>
            <div className="grid grid-2">
              <div className="form-group">
                <label>Participant ID</label>
                <input
                  type="text"
                  value={participantForm.participant_id}
                  onChange={e => setParticipantForm({ ...participantForm, participant_id: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Name (optional)</label>
                <input
                  type="text"
                  value={participantForm.name}
                  onChange={e => setParticipantForm({ ...participantForm, name: e.target.value })}
                />
              </div>
            </div>
            <button type="submit">Add Participant</button>
          </form>
        )}

        {participants.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 40, border: '1px dashed var(--border)', borderRadius: 'var(--radius)' }}>
            <p>No participants yet. Add participants to get started.</p>
          </div>
        ) : (
          <table className="table market-table">
            <thead>
              <tr>
                <th>PARTICIPANT</th>
                {session.legs.map(leg => (
                  <th key={leg}>{leg}</th>
                ))}
                <th>TOTAL VALUE</th>
              </tr>
            </thead>
            <tbody>
              {participants.map(p => {
                const allocation = allocations[p.participant_id] || {}
                const value = calculateValue(allocation)
                return (
                  <tr key={p.participant_id}>
                    <td><strong style={{ color: 'var(--accent)' }}>{p.name || p.participant_id}</strong></td>
                    {session.legs.map(leg => (
                      <td key={leg} className="neutral">{allocation[leg]?.toFixed(2) || '0.00'}</td>
                    ))}
                    <td><strong style={{ color: 'var(--terminal-green)' }}>${value.toFixed(2)}</strong></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {settlement && (
        <div className="card">
          <h2>SETTLEMENT</h2>
          <p style={{ marginBottom: 15, color: 'var(--text-secondary)' }}>
            <strong>Settled at:</strong> {new Date(settlement.settled_at).toLocaleString()}
          </p>
          <table className="table market-table">
            <thead>
              <tr>
                <th>PARTICIPANT</th>
                <th>FINAL PAYOUT</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(settlement.payouts).map(([pid, payout]) => (
                <tr key={pid}>
                  <td><strong style={{ color: 'var(--accent)' }}>{pid}</strong></td>
                  <td><strong style={{ color: 'var(--terminal-yellow)', fontSize: '1.1rem' }}>${payout.toFixed(2)}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {session.status === 'active' && Object.keys(prices).length > 0 && (
        <div className="card">
          <button onClick={handleSettle} className="danger">SETTLE SESSION</button>
        </div>
      )}
    </div>
  )
}
