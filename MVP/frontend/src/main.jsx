import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Portfolio from './pages/Portfolio'
import Trading from './pages/Trading'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/session/:sessionId/portfolio" element={<Portfolio />} />
        <Route path="/session/:sessionId/trading" element={<Trading />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
