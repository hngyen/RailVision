import { useEffect, useState } from "react"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"

function App() {
  const [delays, setDelays] = useState([])
  const [byHour, setByHour] = useState([])

  useEffect(() => {
    fetch("http://localhost:8000/analytics/worst-lines")
      .then(res => res.json())
      .then(data => setDelays(data))

    fetch("http://localhost:8000/analytics/delays/by-hour")
      .then(res => res.json())
      .then(data => setByHour(data))
  }, [])

  const delayColor = (delay) => {
    if (delay > 3) return { color: '#f87171' }
    if (delay > 1) return { color: '#facc15' }
    return { color: '#4ade80' }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <h1 className="text-3xl font-bold mb-2">RailVision</h1>
      <p className="text-gray-400 mb-8">NSW Trains Analytics Dashboard</p>

      {/* by hour chart */}
      <div className="bg-gray-900 rounded-xl p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Average Delay by Hour</h2>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={byHour}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="hour" stroke="#9ca3af" tickFormatter={(h) => `${h}:00`} />
            <YAxis stroke="#9ca3af" unit=" min" />
            <Tooltip
              contentStyle={{ backgroundColor: "#111827", border: "none" }}
              formatter={(val) => [`${val} min`, "Avg Delay"]}
              labelFormatter={(h) => `${h}:00`}
            />
            <Bar dataKey="avg_delay_min" fill="#60a5fa" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* worst lines */}
      <div className="bg-gray-900 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">Worst Lines by Delay</h2>
        {delays.map(line => (
          <div key={line.line} className="flex justify-between items-center py-3 border-b border-gray-800">
            <div>
              <span className="font-bold text-blue-400 text-lg">{line.line}</span>
              <span className="text-gray-400 text-sm ml-2">{line.lineName || "Unknown"}</span>
            </div>
            <div className="text-right">
              <span style={delayColor(line.avg_delay_min)} className="font-semibold">
                {line.avg_delay_min} min avg
              </span>
              <span className="text-gray-500 text-sm ml-4">{line.on_time_pct}% on time</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default App