import React from 'react'

export default function PriceBoard({ prices }) {
    if (Object.keys(prices).length === 0) {
        return (
            <div className="card">
                <h2>MARKET DATA</h2>
                <p style={{ color: '#666' }}>No prices yet. Start oracle to see prices.</p>
            </div>
        )
    }

    return (
        <div className="card">
            <h2>MARKET DATA</h2>
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
        </div>
    )
}
