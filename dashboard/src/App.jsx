import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'

const API_URL = 'http://localhost:8000/api/results'

const SYSTEM_COLORS = {
  rag: '#3b82f6',
  coach_agent: '#f59e0b',
  multiagent_pipeline: '#10b981',
}

function classifyEntry(entry) {
  if (entry.blocked_pre_generation) return 'blocked'
  if (entry.adapter_error) return 'error'
  return 'scored'
}

function SummaryCards({ results }) {
  const scored = results.filter((r) => classifyEntry(r) === 'scored')
  const passed = scored.filter((r) => r.faithfulness_passed && r.relevance_passed)
  const blocked = results.filter((r) => classifyEntry(r) === 'blocked')
  const errored = results.filter((r) => classifyEntry(r) === 'error')

  const cards = [
    { label: 'Total Examples', value: results.length, color: '#334155' },
    { label: 'Passed', value: `${passed.length}/${scored.length}`, color: '#10b981' },
    { label: 'Guardrail Blocked', value: blocked.length, color: '#f59e0b' },
    { label: 'Adapter Errors', value: errored.length, color: '#ef4444' },
  ]

  return (
    <div style={{ display: 'flex', gap: '16px', marginBottom: '32px' }}>
      {cards.map((c) => (
        <div key={c.label} style={{
          flex: 1, padding: '20px', borderRadius: '12px',
          background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          borderTop: `3px solid ${c.color}`,
        }}>
          <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '6px' }}>{c.label}</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: c.color }}>{c.value}</div>
        </div>
      ))}
    </div>
  )
}

function ScoreChart({ results }) {
  const scored = results.filter((r) => classifyEntry(r) === 'scored')
  const chartData = scored.map((r) => ({
    id: r.example_id,
    faithfulness: r.faithfulness_score,
    relevance: r.relevance_score,
    target_system: r.target_system,
  }))

  return (
    <div style={{
      background: '#fff', borderRadius: '12px', padding: '20px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '32px',
    }}>
      <h3 style={{ marginTop: 0, marginBottom: '16px', fontSize: '15px', color: '#334155' }}>
        Faithfulness &amp; Relevance by Example
      </h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="id" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" height={70} />
          <YAxis domain={[0, 5]} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="faithfulness" fill="#6366f1" radius={[3, 3, 0, 0]} />
          <Bar dataKey="relevance" fill="#a855f7" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', gap: '16px', marginTop: '12px', fontSize: '12px', color: '#64748b' }}>
        {Object.entries(SYSTEM_COLORS).map(([sys, color]) => (
          <div key={sys} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block' }} />
            {sys}
          </div>
        ))}
      </div>
    </div>
  )
}

function ResultRow({ entry }) {
  const [expanded, setExpanded] = useState(false)
  const kind = classifyEntry(entry)

  const badge = {
    blocked: { text: 'BLOCKED', bg: '#fef3c7', fg: '#92400e' },
    error: { text: 'ERROR', bg: '#fee2e2', fg: '#991b1b' },
    scored: entry.faithfulness_passed && entry.relevance_passed
      ? { text: 'PASS', bg: '#d1fae5', fg: '#065f46' }
      : { text: 'FAIL', bg: '#fee2e2', fg: '#991b1b' },
  }[kind]

  return (
    <div style={{ borderBottom: '1px solid #f1f5f9' }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', gap: '12px',
          padding: '14px 16px', cursor: 'pointer',
        }}
      >
        <span style={{
          fontSize: '11px', fontWeight: 700, padding: '3px 8px', borderRadius: '6px',
          background: badge.bg, color: badge.fg,
        }}>{badge.text}</span>
        <span style={{ fontFamily: 'monospace', fontSize: '13px', color: '#475569', width: '110px' }}>
          {entry.example_id}
        </span>
        <span style={{ fontSize: '13px', color: '#94a3b8', width: '150px' }}>
          {entry.target_system || '-'}
        </span>
        <span style={{ fontSize: '13px', color: '#334155', flex: 1 }}>
          {kind === 'scored'
            ? `faithfulness=${entry.faithfulness_score} relevance=${entry.relevance_score}`
            : kind === 'blocked'
              ? `matched pattern: "${entry.reason}"`
              : entry.adapter_error}
        </span>
        <span style={{ color: '#94a3b8' }}>{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && kind === 'scored' && (
        <div style={{ padding: '0 16px 16px 16px', fontSize: '13px', color: '#475569', lineHeight: 1.6 }}>
          <p><strong>Query:</strong> {entry.query}</p>
          <p><strong>Answer:</strong> {entry.answer}</p>
          <p><strong>Faithfulness reasoning:</strong> {entry.faithfulness_reasoning}</p>
          <p><strong>Relevance reasoning:</strong> {entry.relevance_reasoning}</p>
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(API_URL)
      .then((res) => {
        if (!res.ok) throw new Error('No results yet - run scripts/run_eval.py first')
        return res.json()
      })
      .then(setResults)
      .catch((e) => setError(e.message))
  }, [])

  if (error) {
    return <div style={{ padding: '40px', fontFamily: 'sans-serif', color: '#991b1b' }}>{error}</div>
  }
  if (!results) {
    return <div style={{ padding: '40px', fontFamily: 'sans-serif', color: '#64748b' }}>Loading…</div>
  }

  return (
    <div style={{ background: '#f8fafc', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '32px 20px' }}>
        <h1 style={{ fontSize: '22px', color: '#1e293b', marginBottom: '4px' }}>
          AI Evaluation Dashboard
        </h1>
        <p style={{ color: '#64748b', fontSize: '14px', marginBottom: '28px' }}>
          FitConnect RAG, Coach Agent &amp; Multiagent Pipeline
        </p>

        <SummaryCards results={results} />
        <ScoreChart results={results} />

        <div style={{
          background: '#fff', borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)', overflow: 'hidden',
        }}>
          {results.map((entry) => (
            <ResultRow key={entry.example_id} entry={entry} />
          ))}
        </div>
      </div>
    </div>
  )
}