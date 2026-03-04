import { useState } from "react"

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
const HOURS = Array.from({ length: 24 }, (_, i) => i)

function getColor(delay) {
  if (delay === null) return null
  if (delay <= 0) return "var(--color-success)"
  if (delay <= 1) return "#22a855"
  if (delay <= 2) return "var(--color-warning)"
  if (delay <= 4) return "#d97706"
  return "var(--color-danger)"
}

export default function Heatmap({ data, stationName }) {
  const [hoveredDay, setHoveredDay] = useState(null)
  const [hoveredHour, setHoveredHour] = useState(null)

  // lookup map
  const lookup = {}
  data.forEach(d => {
    lookup[`${d.day}-${d.hour}`] = d.avg_delay_min
  })

  const handleCellEnter = (day, hour) => {
    setHoveredDay(day)
    setHoveredHour(hour)
  }

  const handleCellLeave = () => {
    setHoveredDay(null)
    setHoveredHour(null)
  }

    return (
    <div style={{ width: "100%", overflowX: "auto" }}> 
        <div style={{ color: "var(--color-accent)", fontSize: "1.6rem", letterSpacing: "0.15em", marginBottom: "0.5rem" }}>
        ▸ DELAY HEATMAP — DAY × HOUR
        </div>
        {stationName && <div style={{ color: "var(--color-text-tertiary)", fontSize: "0.7rem", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: "1rem" }}>{stationName.toUpperCase()}</div>}

        {/* container for scrollable heatmap */}
        <div style={{ display: "flex", flexDirection: "column", minWidth: "100%" }}>
          {/* HOURS HEADER */}
          <div style={{ display: "flex", gap: "2px", alignItems: "center", marginBottom: "4px" }}>
            <div style={{ width: "40px", flexShrink: 0 }}></div>
            {HOURS.map(h => (
              <div 
                key={h} 
                className={hoveredHour === h ? "heatmap-hour-highlight" : ""}
                style={{ 
                flex: 1,           
                minWidth: "0",     
                textAlign: "center", 
                color: hoveredHour === h ? "var(--color-accent)" : "var(--color-text-subtle)", 
                fontSize: "0.7rem",
                fontFamily: "var(--font-mono)",
                fontWeight: hoveredHour === h ? "600" : "400",
                transition: "color 0.2s"
              }}>
              {h}
              </div>
            ))}
          </div>

          {/* DAYS ROWS */}
          {DAYS.map((day, dayIndex) => (
            <div key={day} style={{ display: "flex", gap: "2px", alignItems: "center", marginBottom: "2px" }}>
              <div 
                className={hoveredDay === dayIndex ? "heatmap-day-highlight" : ""}
                style={{ 
                  width: "40px",
                  flexShrink: 0,
                  color: hoveredDay === dayIndex ? "var(--color-accent)" : "var(--color-text-subtle)", 
                  fontSize: "0.8rem", 
                  fontFamily: "var(--font-mono)", 
                  textAlign: "right", 
                  paddingRight: "4px",
                  fontWeight: hoveredDay === dayIndex ? "600" : "400",
                  transition: "color 0.2s"
                }}>
              {day}
              </div>
              
              {HOURS.map(hour => {
                const delay = lookup[`${dayIndex + 1}-${hour}`] ?? null
                const bgColor = getColor(delay)
                
                return (
                  <div
                    key={hour}
                    onMouseEnter={() => handleCellEnter(dayIndex, hour)}
                    onMouseLeave={handleCellLeave}
                    title={delay !== null ? `${day} ${hour}:00 — ${delay}m avg delay` : "No data"}
                    style={{
                      flex: 1,
                      minWidth: "0",
                      aspectRatio: "1 / 1",
                      background: bgColor || "var(--color-border-dim)",
                      backgroundImage: bgColor ? "none" : "repeating-linear-gradient(45deg, #1c1917, #1c1917 2px, #0a0a09 2px, #0a0a09 4px)",
                      border: `1px solid var(--color-background)`,
                      cursor: "default",
                      transition: "transform 0.15s, box-shadow 0.15s",
                      transform: hoveredDay === dayIndex && hoveredHour === hour ? "scale(1.1)" : "scale(1)",
                      boxShadow: hoveredDay === dayIndex && hoveredHour === hour ? `0 0 10px rgba(167, 139, 250, 0.5)` : "none",
                      zIndex: hoveredDay === dayIndex && hoveredHour === hour ? 2 : 1
                    }}
                  />
                );
              })}
            </div>
          ))}
        </div>
    </div>
    )
}