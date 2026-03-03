const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
const HOURS = Array.from({ length: 24 }, (_, i) => i)

function getColor(delay) {
  if (delay === null) return "#1c1917"
  if (delay <= 0) return "#14532d"
  if (delay <= 1) return "#166534"
  if (delay <= 2) return "#854d0e"
  if (delay <= 4) return "#c2410c"
  return "#991b1b"
}

export default function Heatmap({ data }) {
  // lookup map
  const lookup = {}
  data.forEach(d => {
    lookup[`${d.day}-${d.hour}`] = d.avg_delay_min
  })

    return (
    <div style={{ width: "100%", overflowX: "hidden" }}> 
        <div style={{ color: "#a78bfa", fontSize: "1.6rem", letterSpacing: "0.15em", marginBottom: "1.25rem" }}>
        ▸ DELAY HEATMAP — DAY × HOUR
        </div>

        {/* HOURS HEADER */}
        <div style={{ display: "flex", gap: "2px", alignItems: "center", marginBottom: "4px", marginLeft: "40px" }}>
        {HOURS.map(h => (
            <div key={h} style={{ 
            flex: 1,           // Each cell takes an equal portion of the row
            minWidth: "0",     // Prevents blowout on small screens
            textAlign: "center", 
            color: "#57534e", 
            fontSize: "max(0.8rem, 0.6vw)", // Scales text with screen width
            fontFamily: "monospace" 
            }}>
            {h}
            </div>
        ))}
        </div>

        {/* DAYS ROWS */}
        {DAYS.map((day, dayIndex) => (
        <div key={day} style={{ display: "flex", gap: "2px", alignItems: "center", marginBottom: "2px" }}>
            <div style={{ width: "40px", color: "#57534e", fontSize: "0.8rem", fontFamily: "monospace", textAlign: "right", paddingRight: "4px", flexShrink: 0 }}>
            {day}
            </div>
            
            {HOURS.map(hour => {
            const delay = lookup[`${dayIndex + 1}-${hour}`] ?? null;
            return (
                <div
                key={hour}
                title={delay !== null ? `${day} ${hour}:00 — ${delay}m avg delay` : "No data"}
                style={{
                    flex: 1,             // Scale width automatically
                    aspectRatio: "1 / 1", // Keeps them perfectly square as they resize
                    background: getColor(delay),
                    border: "1px solid #0a0a09",
                    cursor: "default",
                    minWidth: "4px"      // Prevents them from disappearing entirely
                }}
                />
            );
            })}
        </div>
        ))}
    </div>
    )
}