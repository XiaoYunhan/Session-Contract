import React, { useState } from 'react'
import { api } from '../../lib/api'

export default function RFQForm({ sessionId, participants, legs, onSuccess, onError }) {
    const [showRFQForm, setShowRFQForm] = useState(false)
    const [rfqForm, setRfqForm] = useState({
        requester_id: '',
        leg_from: '',
        leg_to: '',
        amount_from: ''
    })

    async function handleCreateRFQ(e) {
        e.preventDefault()
        try {
            const data = {
                ...rfqForm,
                amount_from: parseFloat(rfqForm.amount_from)
            }
            const rfq = await api.createRFQ(sessionId, data)

            // Reset form
            setShowRFQForm(false)
            setRfqForm({
                requester_id: '',
                leg_from: '',
                leg_to: '',
                amount_from: ''
            })

            if (onSuccess) onSuccess(rfq)
        } catch (err) {
            if (onError) onError(err.message)
        }
    }

    return (
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
                                {legs.map(leg => (
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
                                {legs.map(leg => (
                                    <option key={leg} value={leg}>{leg}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                    <button type="submit">Create RFQ</button>
                </form>
            )}
        </div>
    )
}
