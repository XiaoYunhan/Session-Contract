import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

export default function Dashboard() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState({
    session_id: '',
    legs: 'AAPL,NVDA,META,ORCL',
    q: '100,60,80,120',
    start_mode: 'immediate',
    end_mode: 'manual'
  })

  // State for custom allocations
  const [showCustomAlloc, setShowCustomAlloc] = useState(false)
  const [participants, setParticipants] = useState([{ id: 'participant1', name: '', allocations: {} }])

  useEffect(() => {
    loadSessions()
  }, [])

  async function loadSessions() {
    try {
      setLoading(true)
      const data = await api.listSessions()
      setSessions(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateSession(e) {
    e.preventDefault()
    try {
      const legs = formData.legs.split(',').map(s => s.trim())

      const data = {
        session_id: formData.session_id,
        legs,
        start_mode: formData.start_mode,
        end_mode: formData.end_mode
      }

      // Only include basket quantities if provided (optional when using custom allocations)
      if (formData.q && formData.q.trim()) {
        const q = formData.q.split(',').map(s => parseFloat(s.trim()))
        if (legs.length !== q.length) {
          setError('Number of legs must match number of quantities')
          return
        }
        data.q = q
      }

      await api.createSession(data)

      // If custom allocations, add participants with their initial allocations
      if (showCustomAlloc) {
        for (const p of participants) {
          if (!p.name) continue
          await api.addParticipant(formData.session_id, {
            participant_id: p.name,
            name: p.name,
            initial_allocations: p.allocations  // Include initial allocations
          })
        }
      }

      setShowCreateForm(false)
      setFormData({
        session_id: '',
        legs: 'AAPL,NVDA,META,ORCL',
        q: '100,60,80,120',
        start_mode: 'immediate',
        end_mode: 'manual'
      })
      setShowCustomAlloc(false)
      setParticipants([{ id: 'participant1', name: '', allocations: {} }])
      setSuccess('Session created successfully!')
      setTimeout(() => setSuccess(null), 3000)
      await loadSessions()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDeleteSession(sessionId) {
    if (!window.confirm(`Delete session "${sessionId}"? This cannot be undone.`)) {
      return
    }

    try {
      await api.deleteSession(sessionId)
      setSuccess(`Session "${sessionId}" deleted`)
      setTimeout(() => setSuccess(null), 3000)
      await loadSessions()
    } catch (err) {
      setError(err.message)
    }
  }

  function addParticipant() {
    setParticipants([...participants, {
      id: `participant${participants.length + 1}`,
      name: '',
      allocations: {}
    }])
  }

  function removeParticipant(index) {
    setParticipants(participants.filter((_, i) => i !== index))
  }

  function updateParticipantName(index, name) {
    const updated = [...participants]
    updated[index].name = name
    setParticipants(updated)
  }

  function updateParticipantAllocation(index, leg, value) {
    const updated = [...participants]
    updated[index].allocations[leg] = parseFloat(value) || 0
    setParticipants(updated)
  }

  if (loading) {
    return <div className="container"><div className="loading">Loading sessions</div></div>
  }

  const legs = formData.legs.split(',').map(s => s.trim())

  return (
    <div className="container">
      <div className="header terminal-glow">
        <h1>SESSION CONTRACTS TERMINAL</h1>
        <p>Multi-Asset Allocation Market • Ring-Fenced Collateral • Event-Sourced Ledger</p>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2>ACTIVE SESSIONS</h2>
          <button className="primary" onClick={() => setShowCreateForm(!showCreateForm)}>
            {showCreateForm ? 'CANCEL' : 'NEW SESSION'}
          </button>
        </div>

        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}

        {showCreateForm && (
          <form onSubmit={handleCreateSession} style={{ marginBottom: 20, padding: 20, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
            <div className="grid grid-2">
              <div className="form-group">
                <label>Session ID</label>
                <input
                  type="text"
                  value={formData.session_id}
                  onChange={e => setFormData({ ...formData, session_id: e.target.value })}
                  placeholder="e.g., demo"
                  required
                />
              </div>
              <div className="form-group">
                <label>Legs (comma-separated)</label>
                <input
                  type="text"
                  value={formData.legs}
                  onChange={e => setFormData({ ...formData, legs: e.target.value })}
                  placeholder="e.g., AAPL,NVDA,META,ORCL"
                  required
                />
              </div>
              <div className="form-group">
                <label>Basket Quantities {showCustomAlloc && <span style={{color: 'var(--text-muted)', fontSize: '0.9em'}}>(optional - auto-calculated)</span>}</label>
                <input
                  type="text"
                  value={formData.q}
                  onChange={e => setFormData({ ...formData, q: e.target.value })}
                  placeholder={showCustomAlloc ? "Leave blank to auto-calculate" : "e.g., 100,60,80,120"}
                  required={!showCustomAlloc}
                />
              </div>
              <div className="form-group">
                <label>Start / End Mode</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <select
                    value={formData.start_mode}
                    onChange={e => setFormData({ ...formData, start_mode: e.target.value })}
                    style={{ flex: 1 }}
                  >
                    <option value="immediate">Immediate</option>
                    <option value="manual">Manual</option>
                  </select>
                  <select
                    value={formData.end_mode}
                    onChange={e => setFormData({ ...formData, end_mode: e.target.value })}
                    style={{ flex: 1 }}
                  >
                    <option value="manual">Manual</option>
                    <option value="timed">Timed</option>
                  </select>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 16, marginBottom: 16 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={showCustomAlloc}
                  onChange={e => setShowCustomAlloc(e.target.checked)}
                />
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  Custom Participant Allocations
                </span>
              </label>
            </div>

            {showCustomAlloc && (
              <div style={{ marginTop: 16, padding: 16, background: 'var(--bg-secondary)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                <h3 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase' }}>
                  PARTICIPANT ALLOCATIONS
                </h3>

                {participants.map((p, index) => (
                  <div key={p.id} style={{ marginBottom: 16, padding: 12, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                      <input
                        type="text"
                        placeholder="Participant ID"
                        value={p.name}
                        onChange={e => updateParticipantName(index, e.target.value)}
                        style={{ flex: 1 }}
                      />
                      {participants.length > 1 && (
                        <button
                          type="button"
                          className="danger"
                          onClick={() => removeParticipant(index)}
                          style={{ padding: '0.5rem' }}
                        >
                          REMOVE
                        </button>
                      )}
                    </div>
                    <div className="grid grid-4">
                      {legs.map(leg => (
                        <div key={leg} className="form-group">
                          <label>{leg}</label>
                          <input
                            type="number"
                            step="0.01"
                            placeholder="0"
                            value={p.allocations[leg] || ''}
                            onChange={e => updateParticipantAllocation(index, leg, e.target.value)}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                <button type="button" className="secondary" onClick={addParticipant}>
                  ADD PARTICIPANT
                </button>
              </div>
            )}

            <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
              <button type="submit" className="success">
                CREATE SESSION
              </button>
              <button type="button" className="secondary" onClick={() => {
                setShowCreateForm(false)
                setShowCustomAlloc(false)
                setParticipants([{ id: 'participant1', name: '', allocations: {} }])
              }}>
                CANCEL
              </button>
            </div>
          </form>
        )}

        {sessions.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 40, border: '1px dashed var(--border)', borderRadius: 'var(--radius)' }}>
            <p>No sessions yet. Create one to get started.</p>
          </div>
        ) : (
          <table className="table market-table">
            <thead>
              <tr>
                <th>SESSION ID</th>
                <th>LEGS</th>
                <th>BASKET</th>
                <th>STATUS</th>
                <th>CREATED</th>
                <th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map(session => (
                <tr key={session.session_id}>
                  <td><strong style={{ color: 'var(--accent)' }}>{session.session_id}</strong></td>
                  <td>{session.legs.join(', ')}</td>
                  <td style={{ fontFamily: 'Roboto Mono, monospace', fontSize: '0.75rem' }}>
                    {session.q.map((q, i) => `${session.legs[i]}:${q}`).join(' | ')}
                  </td>
                  <td>
                    <span className={`status-badge status-${session.status}`}>
                      {session.status}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                    {new Date(session.created_at).toLocaleString()}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <Link to={`/session/${session.session_id}/portfolio`}>
                        <button className="secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}>
                          PORTFOLIO
                        </button>
                      </Link>
                      <Link to={`/session/${session.session_id}/trading`}>
                        <button className="primary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}>
                          TRADE
                        </button>
                      </Link>
                      <button
                        className="danger"
                        onClick={() => handleDeleteSession(session.session_id)}
                        style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}
                      >
                        DELETE
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
