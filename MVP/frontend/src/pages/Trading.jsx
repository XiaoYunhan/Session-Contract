import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'
import { WebSocketClient } from '../lib/websocket'

export default function Trading() {
  const { sessionId } = useParams()
  const [session, setSession] = useState(null)
  const [participants, setParticipants] = useState([])
  const [allocations, setAllocations] = useState({})
  const [prices, setPrices] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // RFQ state
  const [showRFQForm, setShowRFQForm] = useState(false)
  const [rfqForm, setRfqForm] = useState({
    requester_id: '',
    leg_from: '',
    leg_to: '',
    amount_from: ''
  })

  // Active RFQs
  const [activeRFQs, setActiveRFQs] = useState([])

  // Quote form
  const [quoteForm, setQuoteForm] = useState({
    rfq_id: '',
    quoter_id: '',
    rate: ''
  })

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

    wsClient.on('rfq_created', (msg) => {
      setActiveRFQs(prev => [...prev, msg.rfq])
    })

    wsClient.on('trade_executed', (msg) => {
      setSuccess('Trade executed successfully!')
      setTimeout(() => setSuccess(null), 3000)
      loadData()
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

      // Try to get prices
      try {
        const pricesData = await api.getLatestPrices(sessionId)
        setPrices(pricesData.prices || {})
      } catch (err) {
        // No prices yet
      }

      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateRFQ(e) {
    e.preventDefault()
    try {
      const data = {
        ...rfqForm,
        amount_from: parseFloat(rfqForm.amount_from)
      }
      const rfq = await api.createRFQ(sessionId, data)
      setActiveRFQs(prev => [...prev, rfq])
      setShowRFQForm(false)
      setRfqForm({
        requester_id: '',
        leg_from: '',
        leg_to: '',
        amount_from: ''
      })
      setSuccess('RFQ created successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleProvideQuote(rfqId) {
    if (!quoteForm.quoter_id || !quoteForm.rate) {
      setError('Please fill in quoter ID and rate')
      return
    }

    try {
      const quote = await api.provideQuote(rfqId, {
        quoter_id: quoteForm.quoter_id,
        rate: parseFloat(quoteForm.rate)
      })
      setSuccess(`Quote provided! Quote ID: ${quote.quote_id}`)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleAcceptQuote(quoteId) {
    if (!window.confirm('Accept this quote and execute trade?')) {
      return
    }

    try {
      await api.acceptQuote(quoteId)
      setSuccess('Quote accepted! Trade executed.')
      setTimeout(() => setSuccess(null), 3000)
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) {
    return <div className="container"><div className="loading">Loading trading view...</div></div>
  }

  if (!session) {
    return <div className="container"><div className="error">Session not found</div></div>
  }

  return (
    <div className="container">
      <div className="header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>TRADING • {session.session_id.toUpperCase()}</h1>
            <span className={`status-badge status-${session.status}`}>{session.status.toUpperCase()}</span>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <Link to={`/session/${sessionId}/portfolio`}>
              <button className="secondary">PORTFOLIO</button>
            </Link>
            <Link to="/">
              <button className="secondary">DASHBOARD</button>
            </Link>
          </div>
        </div>
      </div>

      {error && <div className="card"><div className="error">{error}</div></div>}
      {success && <div className="card"><div className="success">{success}</div></div>}

      <div className="grid grid-2">
        <div className="card">
          <h2>MARKET DATA</h2>
          {Object.keys(prices).length === 0 ? (
            <p style={{ color: '#666' }}>No prices yet. Start oracle to see prices.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Leg</th>
                  <th>Price</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(prices).map(([leg, price]) => (
                  <tr key={leg}>
                    <td><strong>{leg}</strong></td>
                    <td>${price.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h2>CURRENT ALLOCATIONS</h2>
          {Object.keys(allocations).length === 0 ? (
            <p style={{ color: '#666' }}>No allocations yet.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Participant</th>
                  {session.legs.map(leg => (
                    <th key={leg}>{leg}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(allocations).map(([pid, allocation]) => (
                  <tr key={pid}>
                    <td><strong>{pid}</strong></td>
                    {session.legs.map(leg => (
                      <td key={leg}>{allocation[leg]?.toFixed(2) || '0.00'}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2>REQUEST FOR QUOTE (RFQ)</h2>
          <button className={showRFQForm ? 'secondary' : 'primary'} onClick={() => setShowRFQForm(!showRFQForm)}>
            {showRFQForm ? 'CANCEL' : 'CREATE RFQ'}
          </button>
        </div>

        {showRFQForm && (
          <form onSubmit={handleCreateRFQ} style={{ marginBottom: 20, padding: 20, background: '#f8f9fa', borderRadius: 8 }}>
            <div className="grid grid-2">
              <div className="form-group">
                <label>Requester ID</label>
                <select
                  value={rfqForm.requester_id}
                  onChange={e => setRfqForm({ ...rfqForm, requester_id: e.target.value })}
                  required
                >
                  <option value="">Select participant</option>
                  {participants.map(p => (
                    <option key={p.participant_id} value={p.participant_id}>
                      {p.name || p.participant_id}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Amount to Give</label>
                <input
                  type="number"
                  step="0.01"
                  value={rfqForm.amount_from}
                  onChange={e => setRfqForm({ ...rfqForm, amount_from: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Give Leg</label>
                <select
                  value={rfqForm.leg_from}
                  onChange={e => setRfqForm({ ...rfqForm, leg_from: e.target.value })}
                  required
                >
                  <option value="">Select leg</option>
                  {session.legs.map(leg => (
                    <option key={leg} value={leg}>{leg}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Receive Leg</label>
                <select
                  value={rfqForm.leg_to}
                  onChange={e => setRfqForm({ ...rfqForm, leg_to: e.target.value })}
                  required
                >
                  <option value="">Select leg</option>
                  {session.legs.map(leg => (
                    <option key={leg} value={leg}>{leg}</option>
                  ))}
                </select>
              </div>
            </div>
            <button type="submit">Create RFQ</button>
          </form>
        )}

        {activeRFQs.length === 0 ? (
          <p style={{ textAlign: 'center', color: '#666', padding: 40 }}>
            No active RFQs. Create one to start trading!
          </p>
        ) : (
          <div>
            {activeRFQs.map(rfq => (
              <div key={rfq.rfq_id} style={{ padding: 15, border: '1px solid #ddd', borderRadius: 8, marginBottom: 15 }}>
                <div style={{ marginBottom: 10 }}>
                  <strong>RFQ {rfq.rfq_id.substring(0, 8)}...</strong>
                  <span className={`status-badge status-${rfq.status}`} style={{ marginLeft: 10 }}>
                    {rfq.status}
                  </span>
                </div>
                <p>
                  <strong>Requester:</strong> {rfq.requester_id} |{' '}
                  <strong>Swap:</strong> {rfq.amount_from} {rfq.leg_from} → {rfq.leg_to}
                </p>
                {rfq.status === 'open' && (
                  <div style={{ marginTop: 15, padding: 15, background: '#f8f9fa', borderRadius: 8 }}>
                    <h4 style={{ marginBottom: 10 }}>Provide Quote</h4>
                    <div className="grid grid-3">
                      <div className="form-group">
                        <label>Quoter ID</label>
                        <select
                          value={quoteForm.quoter_id}
                          onChange={e => setQuoteForm({ ...quoteForm, quoter_id: e.target.value, rfq_id: rfq.rfq_id })}
                        >
                          <option value="">Select participant</option>
                          {participants.filter(p => p.participant_id !== rfq.requester_id).map(p => (
                            <option key={p.participant_id} value={p.participant_id}>
                              {p.name || p.participant_id}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Rate (amount_to / amount_from)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={quoteForm.rate}
                          onChange={e => setQuoteForm({ ...quoteForm, rate: e.target.value, rfq_id: rfq.rfq_id })}
                          placeholder="e.g., 0.62"
                        />
                      </div>
                      <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                        <button onClick={() => handleProvideQuote(rfq.rfq_id)}>
                          Provide Quote
                        </button>
                      </div>
                    </div>
                    {quoteForm.rate && (
                      <p style={{ marginTop: 10, color: '#666' }}>
                        You will give {rfq.amount_from} {rfq.leg_from} and receive{' '}
                        {(rfq.amount_from * parseFloat(quoteForm.rate || 0)).toFixed(2)} {rfq.leg_to}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
