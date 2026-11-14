import type { MarketRead } from '../lib/types'

export function MarketReadPanel({ read }: { read: MarketRead }) {
  return (
    <section className="panel">
      <header className="panel-head">
        <h2>Market read</h2>
        <span className={`lean ${read.leanTone}`}>{read.lean}</span>
      </header>
      <p className="summary">{read.summary}</p>
      <dl className="rows">
        {read.rows.map((r) => (
          <div key={r.label} className="row">
            <dt>{r.label}</dt>
            <dd>
              <span className={`value ${r.tone}`}>{r.value}</span>
              <span className="detail">{r.detail}</span>
            </dd>
          </div>
        ))}
      </dl>
      <p className="basis">From price and volume indicators only. Regime: {read.regime.toLowerCase()}.</p>
    </section>
  )
}
