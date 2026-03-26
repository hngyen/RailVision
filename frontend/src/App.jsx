import { useEffect, useState } from "react"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import Heatmap from "./Heatmap"
import StationMap from "./StationMap"

const ACCENT = "var(--color-accent)"
const ACCENT_DIM = "var(--color-accent-dim)"

const STATIONS = [
  { name: "Central", id: "200060" },
  { name: "Town Hall", id: "200070" },
  { name: "Wynyard", id: "200080" },
  { name: "Parramatta", id: "215020" },
  { name: "Martin Place", id: "200090" },
  { name: "Chatswood", id: "206710" },
  { name: "Redfern", id: "201510" },
  { name: "Strathfield", id: "213510" },
  { name: "Circular Quay", id: "200010" },
  { name: "Bondi Junction", id: "202220" },
  { name: "Burwood", id: "213410" },
  { name: "Gadigal", id: "2000434" },
  { name: "North Sydney", id: "206010" },
  { name: "Hurstville", id: "222010" },
  { name: "Wolli Creek", id: "220510" },
  { name: "Blacktown", id: "214810" },
  { name: "Epping", id: "212110" },
  { name: "Mascot", id: "202010" },
  { name: "Green Square", id: "201710" },
  { name: "Victoria Cross", id: "2060444" },
  { name: "Ashfield", id: "213110" },
  { name: "Seven Hills", id: "214710" },
  { name: "Sydenham", id: "204410" },
  { name: "Lidcombe", id: "214110" },
  { name: "Museum", id: "200040" },
  { name: "St James", id: "200050" },
  { name: "Kings Cross", id: "201110" },
  { name: "Hornsby", id: "207710" },
  { name: "Rhodes", id: "213810" },
  { name: "Auburn", id: "214410" },
  { name: "Cabramatta", id: "216620" },
  { name: "Liverpool", id: "217010" }
]

function StatCard({ label, value, sub, loading }) {
  return (
    <div className="stat-card-compact" style={{
      border: `1px solid var(--color-accent-dim)`,
      background: "var(--color-surface)",
      padding: "0.75rem 1rem",
      flex: 1,
      minHeight: "80px",
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between"
    }}>
      <div style={{ color: "var(--color-text-tertiary)", fontSize: "0.7rem", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: "0.5rem" }}>{label}</div>
      {loading ? (
        <div className="skeleton-loading" style={{ marginBottom: "0.5rem" }}></div>
      ) : (
        <div style={{ color: ACCENT, fontSize: "2rem", fontFamily: "'Courier New', monospace", fontWeight: "bold", lineHeight: 1 }}>{value}</div>
      )}
      {sub && !loading && <div style={{ color: "var(--color-accent-dim)", fontSize: "0.75rem", marginTop: "0.4rem" }}>{sub}</div>}
    </div>
  )
}

function DelayBadge({ delay }) {
  const color = delay > 3 ? "var(--color-danger)" : delay > 1 ? "var(--color-warning)" : "var(--color-success)"
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

function DepartureBoard({ departures, stationName }) {
  const upcoming = departures.filter(dep => {
    const now = new Date()
    const scheduled = new Date(dep.scheduled_dt)
    return (scheduled - now) / 60000 > -2
  })

        return (
          <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-surface-border)", padding: "1.5rem", marginBottom: "1.5rem" }}>
            <div style={{ color: ACCENT, fontSize: "1.6rem", letterSpacing: "0.15em", marginBottom: "0.5rem" }}>
              ▸ LIVE DEPARTURES
            </div>
            <div style={{ color: "var(--color-text-tertiary)", fontSize: "0.7rem", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: "1rem" }}>{stationName.toUpperCase()}</div>
            <div style={{
              maxHeight: "680px",
              overflowY: "auto",
              paddingRight: "0.5rem"
            }}>
              <div style={{
                display: "grid",
                gridTemplateColumns: "60px 1fr 1fr 80px 80px",
                gap: "0 1rem",
                color: "var(--color-text-subtle)",
                fontSize: "0.65rem",
                letterSpacing: "0.1em",
                marginBottom: "0.75rem",
                paddingBottom: "0.5rem",
                borderBottom: "1px solid var(--color-border-dim)",
                position: "sticky",
                top: 0,
                background: "var(--color-surface)",
                zIndex: 1
              }}>
                <span>LINE</span>
                <span>DESTINATION</span>
                <span>PLATFORM</span>
                <span style={{ textAlign: "right" }}>SCHED</span>
                <span style={{ textAlign: "right" }}>STATUS</span>
              </div>
              {upcoming.slice(0, 50).map((dep, i) => {
                const now = new Date()
                const scheduled = new Date(dep.scheduled_dt)
                const estimated = dep.estimated_dt ? new Date(dep.estimated_dt) : null
                const delayMins = estimated ? Math.round((estimated - scheduled) / 60000) : null
                const status = !dep.realtime ? "—" : delayMins === null ? "—" : isNaN(delayMins) ? "—" : delayMins <= 0 ? "ON TIME" : `+${delayMins}m`
                const statusColor = !dep.realtime ? "var(--color-text-subtle)" : delayMins <= 0 ? "var(--color-success)" : delayMins <= 2 ? "var(--color-warning)" : "var(--color-danger)"
                const minsUntil = Math.round((scheduled - now) / 60000)

                return (
                  <div key={i} style={{
                    display: "grid",
                    gridTemplateColumns: "60px 1fr 1fr 80px 80px",
                    gap: "0 1rem",
                    padding: "0.6rem 0",
                    borderBottom: "1px solid var(--color-border-dim)",
                    fontSize: "0.8rem",
                  }}>
                    <span style={{ color: ACCENT, fontWeight: "bold" }}>{dep.line}</span>
                    <span style={{ color: "var(--color-text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {dep.destination?.split(",")[0]}
                    </span>
                    <span style={{ color: "var(--color-text-light)", fontSize: "0.75rem" }}>{dep.platform}</span>
                    <span style={{ textAlign: "right", color: "var(--color-text-light)" }}>
                      {minsUntil <= 0 ? "NOW" : minsUntil <= 60 ? `${minsUntil}m` : scheduled.toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit" })}
                    </span>
                    <span style={{ textAlign: "right", color: statusColor, fontSize: "0.7rem", letterSpacing: "0.05em" }}>{status}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}


export default function App() {
  const [selectedStation, setSelectedStation] = useState(STATIONS[0]) // Central default
  const [delays, setDelays] = useState([]);
  const [byHour, setByHour] = useState([]);
  const [loading, setLoading] = useState(true);
  const [byDayHour, setByDayHour] = useState(true);
  const [liveDeps, setLiveDeps] = useState([]);
  const [stationStats, setStationStats] = useState({})
  const [activeTab, setActiveTab] = useState("overview")
  const tabs = ["overview", "analytics"]
  const API = "https://railvision-app-jpl5c.ondigitalocean.app";

  const filteredStations = STATIONS.filter(s => 
    s.name.toLowerCase().includes("")
  )

  const handleStationChange = (station) => {
    setSelectedStation(station)
  }

  const fetchData = () => {
      setLoading(true);
      Promise.all([
        fetch(`${API}/analytics/worst-lines?stop_id=${selectedStation.id}`).then(r => r.json()),
        fetch(`${API}/analytics/delays/by-hour?stop_id=${selectedStation.id}`).then(r => r.json()),
        fetch(`${API}/departures/live/${selectedStation.id}`).then(r => r.json()),
        fetch(`${API}/analytics/delays/by-day-hour?stop_id=${selectedStation.id}`).then(r => r.json()),
        fetch(`${API}/analytics/stations/summary`).then(r => r.json()),
      ]).then(([d, h, live, dayHour, stats]) => {
        setDelays(Array.isArray(d) ? d : [])
        setByHour(Array.isArray(h) ? h : [])
        setLiveDeps(Array.isArray(live) ? live : [])
        setByDayHour(Array.isArray(dayHour) ? dayHour : [])
        setStationStats(stats || {})
        setLoading(false)
      })
    }

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [selectedStation])
    
  const totalTrips = Array.isArray(delays) ? delays.reduce((s, l) => s + l.total_trips, 0) : 0
  const avgDelay = Array.isArray(delays) && delays.length ? (delays.reduce((s, l) => s + l.avg_delay_min, 0) / delays.length).toFixed(2) : 0
  const worstLine = Array.isArray(delays) && delays[0]?.line ? delays[0].line : "—"
  
  // calculate daily average, bc railvision collection not uniform
  const getDaysTracked = () => {
    const trackingDates = {
      "200060": 4, // Central: March 1-4 = 4 days
      "default": 2  // Others: March 3-4 = 2 days
    }
    return trackingDates[selectedStation.id] || trackingDates.default
  }
  const dailyAvg = totalTrips > 0 ? (totalTrips / getDaysTracked()).toFixed(0) : 0
  const daysTracked = getDaysTracked()
  const hasHistoricalData = dailyAvg >= 5  // threshold for realistic data

  return (
      <>
        {/* Progress bar */}
        <div className="progress-bar"></div>

        <div style={{ minHeight: "100vh", background: "var(--color-background)", color: "var(--color-text)", fontFamily: "'Courier New', monospace", padding: "2.5rem" }}>
          
          {/* header */}
          <div style={{ borderBottom: `1px solid var(--color-accent-dim)`, paddingBottom: "1.5rem", marginBottom: "2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "1rem" }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: "1rem" }}>
        <h1 style={{ fontSize: "3rem", fontWeight: "bold", color: ACCENT, margin: 0, letterSpacing: "0.05em", textShadow: "0 0 10px rgba(167, 139, 250, 0.5)" }}>RAILVISION</h1>
                <span style={{ color: "var(--color-secondary)", fontSize: "1rem", letterSpacing: "0.1em" }}>NSW TRAINS ANALYTICS</span>
              </div>
              <div style={{ color: "var(--color-secondary)", fontSize: "0.75rem", letterSpacing: "0.08em", textAlign: "right" }}>
                <div>LIVE DATA<span className="live-indicator"></span></div>
                <div>UPDATES EVERY 60S</div>
              </div>
            </div>
          </div>
        
          {/* tab bar */}
          <div style={{ display: "flex", gap: "0", marginBottom: "2rem", borderBottom: `1px solid var(--color-accent-dim)` }}>
            {tabs.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  background: "none",
                  border: "none",
                  borderBottom: activeTab === tab ? `2px solid var(--color-accent)` : "2px solid transparent",
                  color: activeTab === tab ? ACCENT : "var(--color-text-subtle)",
                  padding: "0.75rem 1.5rem",
                  fontFamily: "monospace",
                  fontSize: "0.8rem",
                  letterSpacing: "0.15em",
                  textTransform: "uppercase",
                  cursor: "pointer",
                  marginBottom: "-1px"
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="app-container">
            {/* Sidebar - map as main navigation tool */}
            <div className="map-sidebar">
              {/* cmd line input */}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1rem" }}>
                <label style={{ color: "var(--color-text-subtle)", fontSize: "0.6rem", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                  &gt; SELECT TERMINAL
                </label>
                <select
                  value={selectedStation.id}
                  onChange={(e) => {
                    const station = STATIONS.find(s => s.id === e.target.value)
                    if (station) handleStationChange(station)
                  }}
                  className="command-input"
                  style={{
                    width: "100%",
                    padding: "0.6rem",
                    background: "var(--color-surface)",
                    border: `1px solid var(--color-accent-dim)`,
                    color: ACCENT,
                    fontFamily: "monospace",
                    cursor: "pointer"
                  }}
                >
                  {STATIONS.map(s => (
                    <option key={s.id} value={s.id} style={{ background: "var(--color-background)", color: ACCENT }}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* map container */}
              <div style={{ height: "450px", width: "450px", border: `1px solid var(--color-accent-dim)`, marginBottom: "1rem" }} className="map-container">
                <StationMap stationStats={stationStats} selectedStation={selectedStation} onStationSelect={handleStationChange} />
              </div>

              {/* quick stat cards */}
              <div style={{ marginBottom: "0.5rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
                  <span style={{ color: "var(--color-text-tertiary)", fontSize: "0.7rem", letterSpacing: "0.15em", textTransform: "uppercase" }}>Stats Info</span>
                  <span title="Central: tracking since March 1. Other stations: tracking since March 3." style={{ cursor: "help", color: ACCENT, fontSize: "0.8rem", width: "18px", height: "18px", display: "flex", alignItems: "center", justifyContent: "center", border: `1px solid ${ACCENT}`, borderRadius: "50%", fontWeight: "bold", flexShrink: 0 }}>?</span>
                </div>
              </div>
              <div className="stat-cards-container">
                <StatCard label="Total Trips" value={totalTrips.toLocaleString()} loading={loading} />
                <StatCard label="Daily Avg" value={dailyAvg} sub="trips/day" loading={loading} />
                <StatCard label="Days Tracked" value={daysTracked} loading={loading} />
                <StatCard label="Avg Delay" value={`${avgDelay}m`} loading={loading} />
                <StatCard label="Worst Line" value={worstLine} loading={loading} />
                <StatCard label="Lines Tracked" value={delays.length} loading={loading} />
              </div>
            </div>

            {/* Main Content */}
            <div className="main-content" style={{ position: "relative" }}>
              {activeTab === "overview" && (
                <div>
                  {/* Live Departures */}
                  <DepartureBoard departures={liveDeps} stationName={selectedStation.name} />
                </div>
              )}

              {activeTab === "analytics" && (
                <div>
                  {!hasHistoricalData ? (
                    <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-surface-border)", padding: "2rem", marginBottom: "1.5rem", textAlign: "center", minHeight: "300px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                      <div style={{ color: ACCENT, fontSize: "1.6rem", letterSpacing: "0.15em", marginBottom: "1rem" }}>
                        ▸ HISTORICAL DATA UNAVAILABLE
                      </div>
                      <div style={{ color: "var(--color-text-tertiary)", fontSize: "0.8rem", letterSpacing: "0.05em", maxWidth: "400px" }}>
                        This station has insufficient historical data ({dailyAvg} trips/day). Check back later as we collect more data, or view live departures on the overview tab.
                      </div>
                    </div>
                  ) : (
                    <>
                  {/* Hourly Chart */}
                  <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-surface-border)", padding: "1.5rem", marginBottom: "1.5rem", minHeight: "300px" }}>
                    <div style={{ color: ACCENT, fontSize: "1.6rem", letterSpacing: "0.15em", marginBottom: "0.5rem" }}>
                      ▸ AVG DELAY BY HOUR (SYDNEY LOCAL TIME)
                    </div>
                    <div style={{ color: "var(--color-text-tertiary)", fontSize: "0.7rem", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: "1rem" }}>{selectedStation.name.toUpperCase()}</div>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={byHour} barCategoryGap="20%">
                        <CartesianGrid strokeDasharray="2 4" stroke="var(--color-secondary)" vertical={false} />
                        <XAxis dataKey="hour" stroke={ACCENT} tick={{ fill: ACCENT, fontSize: 11, angle: -45, textAnchor: "end", height: 80 }} tickFormatter={h => `${h}:00`} />
                        <YAxis stroke="var(--color-text-subtle)" tick={{ fill: ACCENT, fontSize: 11 }} unit="m" width={35} />
                        <Tooltip
                          contentStyle={{ background: "var(--color-background)", border: `1px solid var(--color-accent-dim)`, borderRadius: 0, fontFamily: "monospace", fontSize: "0.75rem", color: "var(--color-text)" }}
                          formatter={val => [`${val} min`, "Avg Delay"]}
                          labelFormatter={h => `${h}:00`}
                          cursor={{ fill: "var(--color-border-dim)" }}
                        />
                        <Bar dataKey="avg_delay_min" fill={ACCENT} radius={0} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Heatmap */}
                  <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-surface-border)", padding: "1.5rem", marginBottom: "1.5rem", minHeight: "400px" }}>
                    <Heatmap data={byDayHour} stationName={selectedStation.name} />
                  </div>

                  {/* Line Performance Rankings */}
                  <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-surface-border)", padding: "1.5rem" }}>
                    <div style={{ color: ACCENT, fontSize: "1.6rem", letterSpacing: "0.15em", marginBottom: "0.5rem" }}>
                      ▸ LINE PERFORMANCE RANKING
                    </div>
                    <div style={{ color: "var(--color-text-tertiary)", fontSize: "0.7rem", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: "1rem" }}>{selectedStation.name.toUpperCase()}</div>
                    <div style={{ display: "grid", gridTemplateColumns: "80px 1fr 100px 100px 80px", gap: "0 1rem", color: "var(--color-secondary)", fontSize: "0.8rem", letterSpacing: "0.1em", marginBottom: "0.75rem", paddingBottom: "0.5rem", borderBottom: "1px solid var(--color-border-dim)" }}>
                      <span>LINE</span><span>NAME</span><span style={{ textAlign: "right" }}>AVG DELAY</span><span style={{ textAlign: "right" }}>ON TIME</span><span style={{ textAlign: "right" }}>STATUS</span>
                    </div>
                    {delays.map((line, i) => (
                      <div key={line.line} className="performance-row" style={{
                        display: "grid",
                        gridTemplateColumns: "80px 1fr 100px 100px 80px",
                        gap: "0 1rem",
                        padding: "0.6rem 0",
                        borderBottom: "1px solid var(--color-border-dim)",
                        fontSize: "0.9rem",
                        opacity: loading ? 0.4 : 1,
                        transition: "background-color 0.2s, box-shadow 0.2s",
                        cursor: "default"
                      }}>
                        <span style={{ color: ACCENT, fontWeight: "bold" }}>{line.line}</span>
                        <span style={{ color: "var(--color-text)", fontSize: "0.9rem", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{line.lineName || "—"}</span>
                        <span style={{ textAlign: "right", color: line.avg_delay_min > 3 ? "var(--color-danger)" : line.avg_delay_min > 1 ? "var(--color-warning)" : "var(--color-success)" }}>
                          {line.avg_delay_min}m
                        </span>
                        <span style={{ textAlign: "right", color: "var(--color-secondary)" }}>{line.on_time_pct}%</span>
                        <span style={{ textAlign: "right" }}><DelayBadge delay={line.avg_delay_min} /></span>
                      </div>
                    ))}
                  </div>
                    </>
                  )}
                  </div>
              )}
              
              {/* Loading Overlay */}
              {loading && (
                <div className="content-loading-overlay" style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: "rgba(10, 10, 9, 0.7)",
                  backdropFilter: "blur(2px)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  zIndex: 50,
                  borderRadius: "0.25rem"
                }}>
                  <div style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "1rem"
                  }}>
                    <div className="skeleton-loading" style={{
                      width: "40px",
                      height: "6px",
                      marginBottom: "0.5rem"
                    }}></div>
                    <div style={{
                      color: "var(--color-text-tertiary)",
                      fontSize: "0.75rem",
                      letterSpacing: "0.1em",
                      textTransform: "uppercase"
                    }}>SYNCING DATA</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div style={{ color: "var(--color-footer)", fontSize: "0.65rem", marginTop: "1.5rem", letterSpacing: "0.08em" }}>
            DATA SOURCE: TRANSPORT FOR NSW OPEN DATA // POLLING INTERVAL 60S
          </div>
        </div>
      </>
    )
}