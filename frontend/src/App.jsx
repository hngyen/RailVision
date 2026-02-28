import { useEffect, useState } from "react"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"

const ACCENT = "#a78bfa"      // violet
const ACCENT_DIM = "#3b1f6e"  // dark purple

function StatCard({ label, value, sub }) {
  return (
    <div style={{
      border: `1px solid #3b1f6e`,
      background: "#0f0f0e",
      padding: "1.25rem 1.5rem",
      flex: 1,
    }}>
      <div style={{ color: "#78716c", fontSize: "0.7rem", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: "0.5rem" }}>{label}</div>
      <div style={{ color: ACCENT, fontSize: "2rem", fontFamily: "'Courier New', monospace", fontWeight: "bold", lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ color: "#57534e", fontSize: "0.75rem", marginTop: "0.4rem" }}>{sub}</div>}
    </div>
  )
}

function DelayBadge({ delay }) {
  const color = delay > 3 ? "#ef4444" : delay > 1 ? "#eab308" : "#22c55e"
  const label = delay > 3 ? "DELAYED" : delay > 1 ? "SLOW" : "ON TIME"
  return (
    <span style={{
      color,
      border: `1px solid ${color}`,
      fontSize: "0.6rem",
      letterSpacing: "0.1em",
      padding: "2px 6px",
      marginLeft: "0.5rem",
      fontFamily: "monospace"
    }}>{label}</span>
  )
}

function DepartureBoard({ departures }) {
        const now = new Date(new Date().toLocaleString("en-AU", { timeZone: "Australia/Sydney" }))
        return (
          <div style={{ background: "#0f0f0e", border: "1px solid #292524", padding: "1.5rem", marginBottom: "1.5rem" }}>
            <div style={{ color: "#78716c", fontSize: "0.7rem", letterSpacing: "0.15em", marginBottom: "1.25rem" }}>
              ▸ LIVE DEPARTURES — CENTRAL STATION
            </div>
            <div style={{
              display: "grid",
              gridTemplateColumns: "60px 1fr 1fr 80px 80px",
              gap: "0 1rem",
              color: "#57534e",
              fontSize: "0.65rem",
              letterSpacing: "0.1em",
              marginBottom: "0.75rem",
              paddingBottom: "0.5rem",
              borderBottom: "1px solid #1c1917"
            }}>
              <span>LINE</span>
              <span>DESTINATION</span>
              <span>PLATFORM</span>
              <span style={{ textAlign: "right" }}>SCHED</span>
              <span style={{ textAlign: "right" }}>STATUS</span>
            </div>
            {departures.slice(0, 12).map((dep, i) => {
              const scheduled = new Date(new Date(dep.scheduled_dt).toLocaleString("en-AU", { timeZone: "Australia/Sydney" }))
              const estimated = dep.estimated_dt ? new Date(dep.estimated_dt) : null
              const delayMins = estimated ? Math.round((estimated - scheduled) / 60000) : 0
              const status = !dep.realtime ? "—" : delayMins <= 0 ? "ON TIME" : delayMins <= 2 ? `+${delayMins}m` : `+${delayMins}m`
              const statusColor = !dep.realtime ? "#57534e" : delayMins <= 0 ? "#22c55e" : delayMins <= 2 ? "#eab308" : "#ef4444"
              const minsUntil = Math.round((scheduled - now) / 60000)

              return (
                <div key={i} style={{
                  display: "grid",
                  gridTemplateColumns: "60px 1fr 1fr 80px 80px",
                  gap: "0 1rem",
                  padding: "0.6rem 0",
                  borderBottom: "1px solid #1c1917",
                  fontSize: "0.8rem",
                }}>
                  <span style={{ color: ACCENT, fontWeight: "bold" }}>{dep.line}</span>
                  <span style={{ color: "#e7e5e4", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {dep.destination?.split(",")[0]}
                  </span>
                  <span style={{ color: "#a8a29e", fontSize: "0.75rem" }}>{dep.platform}</span>
                  <span style={{ textAlign: "right", color: "#a8a29e" }}>
                    {minsUntil <= 0 ? "NOW" : minsUntil <= 60 ? `${minsUntil}m` : scheduled.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <span style={{ textAlign: "right", color: statusColor, fontSize: "0.7rem", letterSpacing: "0.05em" }}>{status}</span>
                </div>
              )
            })}
          </div>
        )}

export default function App() {
  const [delays, setDelays] = useState([])
  const [byHour, setByHour] = useState([])
  const [loading, setLoading] = useState(true)
  const [liveDeps, setLiveDeps] = useState([])

  useEffect(() => {
    const fetchData = () => {
      Promise.all([
        fetch("https://railvision-backend.onrender.com/analytics/worst-lines").then(r => r.json()),
        fetch("https://railvision-backend.onrender.com/analytics/delays/by-hour").then(r => r.json()),
        fetch("https://railvision-backend.onrender.com/departures/live/200060").then(r => r.json()).then(setLiveDeps),
      ]).then(([d, h]) => {
        setDelays(d)
        setByHour(h)
        setLoading(false)
      })
    }
    fetchData() // run immediately
    const interval = setInterval(fetchData, 60000) // then every 60s
    return () => clearInterval(interval) // cleanup on unmount
  }, [])

  const totalTrips = delays.reduce((s, l) => s + l.total_trips, 0)
  const avgDelay = delays.length ? (delays.reduce((s, l) => s + l.avg_delay_min, 0) / delays.length).toFixed(2) : 0
  const worstLine = delays[0]?.line ?? "—"

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a09",
      color: "#e7e5e4",
      fontFamily: "'Courier New', monospace",
      padding: "2.5rem",
    }}>
      {/* header */}
      <div style={{ borderBottom: `1px solid ${ACCENT_DIM}`, paddingBottom: "1.5rem", marginBottom: "2rem" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "1rem" }}>
          <h1 style={{ fontSize: "3rem", fontWeight: "bold", color: ACCENT, margin: 0, letterSpacing: "0.05em" }}>
            RAILVISION
          </h1>
          <span style={{ color: "#cdbdd4", fontSize: "1rem", letterSpacing: "0.1em" }}>
            NSW TRAINS ANALYTICS // CENTRAL STATION
          </span>
        </div>
        <div style={{ color: "#cdbdd4", fontSize: "0.95rem", marginTop: "0.4rem", letterSpacing: "0.08em" }}>
          LIVE DATA — UPDATES EVERY 60S
        </div>
      </div>

      <DepartureBoard departures={liveDeps} />

      {/* stat cards */}
      {!loading && (
        <div style={{ display: "flex", gap: "1px", marginBottom: "2rem", background: "#292524" }}>
          <StatCard label="Total Trips Recorded" value={totalTrips.toLocaleString()} />
          <StatCard label="Network Avg Delay" value={`${avgDelay}m`} />
          <StatCard label="Worst Line Today" value={worstLine} />
          <StatCard label="Lines Tracked" value={delays.length} />
        </div>
      )}

      {/* chart */}
      <div style={{ background: "#0f0f0e", border: "1px solid #292524", padding: "1.5rem", marginBottom: "1.5rem" }}>
        <div style={{ color: "#a78bfa", fontSize: "1.6rem", letterSpacing: "0.15em", marginBottom: "1.25rem" }}>
          ▸ AVG DELAY BY HOUR (SYDNEY LOCAL TIME)
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={byHour} barCategoryGap="30%">
            <CartesianGrid strokeDasharray="2 4" stroke="#cdbdd4" vertical={false} />
            <XAxis dataKey="hour" stroke="#a78bfa" tick={{ fill: "#733dd6", fontSize: 18 }} tickFormatter={h => `${h}:00`} />
            <YAxis stroke="#57534e" tick={{ fill: "#733dd6", fontSize: 11 }} unit="m" width={35} />
            <Tooltip
              contentStyle={{ background: "#0a0a09", border: `1px solid ${ACCENT_DIM}`, borderRadius: 0, fontFamily: "monospace", fontSize: "0.75rem" }}
              formatter={val => [`${val} min`, "Avg Delay"]}
              labelFormatter={h => `${h}:00`}
              cursor={{ fill: "#1c1917" }}
            />
            <Bar dataKey="avg_delay_min" fill={ACCENT} radius={0} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* lines table */}
      <div style={{ background: "#0f0f0e", border: "1px solid #292524", padding: "1.5rem" }}>
        <div style={{ color: "#a78bfa", fontSize: "1.6rem", letterSpacing: "0.15em", marginBottom: "1.25rem" }}>
          ▸ LINE PERFORMANCE RANKING
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "80px 1fr 100px 100px 80px", gap: "0 1rem", color: "#cdbdd4", fontSize: "0.8rem", letterSpacing: "0.1em", marginBottom: "0.75rem", paddingBottom: "0.5rem", borderBottom: "1px solid #1c1917" }}>
          <span>LINE</span><span>NAME</span><span style={{ textAlign: "right" }}>AVG DELAY</span><span style={{ textAlign: "right" }}>ON TIME</span><span style={{ textAlign: "right" }}>STATUS</span>
        </div>
        {delays.map((line, i) => (
          <div key={line.line} style={{
            display: "grid",
            gridTemplateColumns: "80px 1fr 100px 100px 80px",
            gap: "0 1rem",
            padding: "0.6rem 0",
            borderBottom: "1px solid #2e2a28",
            fontSize: "0.9rem",
            opacity: loading ? 0.4 : 1,
          }}>
            <span style={{ color: ACCENT, fontWeight: "bold" }}>{line.line}</span>
            <span style={{ color: "#d8d1cd", fontSize: "0.9rem", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{line.lineName || "—"}</span>
            <span style={{ textAlign: "right", color: line.avg_delay_min > 3 ? "#ef4444" : line.avg_delay_min > 1 ? "#eab308" : "#22c55e" }}>
              {line.avg_delay_min}m
            </span>
            <span style={{ textAlign: "right", color: "#cfc8c3" }}>{line.on_time_pct}%</span>
            <span style={{ textAlign: "right" }}><DelayBadge delay={line.avg_delay_min} /></span>
          </div>
        ))}
      </div>

      <div style={{ color: "#44403c", fontSize: "0.65rem", marginTop: "1.5rem", letterSpacing: "0.08em" }}>
        DATA SOURCE: TRANSPORT FOR NSW OPEN DATA // POLLING INTERVAL 60S
      </div>
    </div>
  )
}