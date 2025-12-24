import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'
import { WebSocketClient } from '../lib/websocket'
import PriceBoard from '../components/market/PriceBoard'
import RFQForm from '../components/trading/RFQForm'
import ActiveRFQs from '../components/trading/ActiveRFQs'

export default function Trading() {
  const { sessionId } = useParams()
  const [session, setSession] = useState(null)
  const [participants, setParticipants] = useState([])
  const [allocations, setAllocations] = useState({})
  const [prices, setPrices] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Active RFQs
  const [activeRFQs, setActiveRFQs] = useState([])

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

  // Unused in UI currently, but kept for future use
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
        <PriceBoard prices={prices} />

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

      <RFQForm
        sessionId={sessionId}
        participants={participants}
        legs={session.legs}
        onSuccess={(rfq) => {
          setActiveRFQs(prev => [...prev, rfq])
          setSuccess('RFQ created successfully!')
          setTimeout(() => setSuccess(null), 3000)
        }}
        onError={(msg) => setError(msg)}
      />

      <ActiveRFQs
        rfqs={activeRFQs}
        participants={participants}
        onQuoteProvided={(quote) => {
          setSuccess(`Quote provided! Quote ID: ${quote.quote_id}`)
          setTimeout(() => setSuccess(null), 3000)
        }}
      />
    </div>
  )
}
