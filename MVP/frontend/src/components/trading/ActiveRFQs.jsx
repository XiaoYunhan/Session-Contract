import React, { useState } from 'react'
import { api } from '../../lib/api'

export default function ActiveRFQs({ rfqs, participants, onQuoteProvided }) {
    const [quoteForm, setQuoteForm] = useState({
        rfq_id: '',
        quoter_id: '',
        rate: ''
    })
    const [error, setError] = useState(null)

    async function handleProvideQuote(rfqId) {
        if (!quoteForm.quoter_id || !quoteForm.rate) {
            setError('Please fill in quoter ID and rate')
            return
        }
        setError(null)

        try {
            const quote = await api.provideQuote(rfqId, {
                quoter_id: quoteForm.quoter_id,
                rate: parseFloat(quoteForm.rate)
            })

            // Reset form
            setQuoteForm(prev => ({ ...prev, rate: '', quoter_id: '' }))

            if (onQuoteProvided) onQuoteProvided(quote)
        } catch (err) {
            setError(err.message)
        }
    }

    if (rfqs.length === 0) {
        return (
            <div className="card">
                <h2>ACTIVE RFQs</h2>
                <p style={{ textAlign: 'center', color: '#666', padding: 40 }}>
                    No active RFQs. Create one to start trading!
                </p>
            </div>
        )
    }

    return (
        <div className="card">
            <h2>ACTIVE RFQs</h2>
            {error && <div className="error" style={{ marginBottom: 15 }}>{error}</div>}

            <div>
                {rfqs.map(rfq => (
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
                                            value={quoteForm.rfq_id === rfq.rfq_id ? quoteForm.quoter_id : ''}
                                            onChange={e => setQuoteForm({ rfq_id: rfq.rfq_id, quoter_id: e.target.value, rate: quoteForm.rfq_id === rfq.rfq_id ? quoteForm.rate : '' })}
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
                                            value={quoteForm.rfq_id === rfq.rfq_id ? quoteForm.rate : ''}
                                            onChange={e => setQuoteForm({ rfq_id: rfq.rfq_id, rate: e.target.value, quoter_id: quoteForm.rfq_id === rfq.rfq_id ? quoteForm.quoter_id : '' })}
                                            placeholder="e.g., 0.62"
                                        />
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                                        <button onClick={() => handleProvideQuote(rfq.rfq_id)}>
                                            Provide Quote
                                        </button>
                                    </div>
                                </div>
                                {quoteForm.rfq_id === rfq.rfq_id && quoteForm.rate && (
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
        </div>
    )
}
