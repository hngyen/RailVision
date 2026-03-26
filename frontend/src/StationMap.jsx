import { useEffect, useRef } from "react"
import L from "leaflet"
import "leaflet/dist/leaflet.css"

const STATION_COORDS = {
  "200060": { name: "Central", lat: -33.8833, lng: 151.2057 },
  "200070": { name: "Town Hall", lat: -33.8731, lng: 151.2071 },
  "200080": { name: "Wynyard", lat: -33.8660, lng: 151.2057 },
  "215020": { name: "Parramatta", lat: -33.8148, lng: 151.0017 },
  "200090": { name: "Martin Place", lat: -33.8675, lng: 151.2108 },
  "206710": { name: "Chatswood", lat: -33.7991, lng: 151.1795 },
  "201510": { name: "Redfern", lat: -33.8924, lng: 151.2037 },
  "213510": { name: "Strathfield", lat: -33.8742, lng: 151.0917 },
  "200010": { name: "Circular Quay", lat: -33.8612, lng: 151.2105 },
  "202220": { name: "Bondi Junction", lat: -33.8913, lng: 151.2483 },
  "213410": { name: "Burwood", lat: -33.8767, lng: 151.1039 },
  "2000434": { name: "Gadigal", lat: -33.8748, lng: 151.2081 },
  "206010": { name: "North Sydney", lat: -33.8400, lng: 151.2065 },
  "222010": { name: "Hurstville", lat: -33.9669, lng: 151.1034 },
  "220510": { name: "Wolli Creek", lat: -33.9287, lng: 151.1524 },
  "214810": { name: "Blacktown", lat: -33.7718, lng: 150.9066 },
  "212110": { name: "Epping", lat: -33.7725, lng: 151.1026 },
  "202010": { name: "Mascot", lat: -33.9234, lng: 151.1925 },
  "201710": { name: "Green Square", lat: -33.9061, lng: 151.2030 },
  "2060444": { name: "Victoria Cross", lat: -33.8378, lng: 151.2058 },
  "213110": { name: "Ashfield", lat: -33.8876, lng: 151.1278 },
  "214710": { name: "Seven Hills", lat: -33.7744, lng: 150.9351 },
  "204410": { name: "Sydenham", lat: -33.9152, lng: 151.1661 },
  "214110": { name: "Lidcombe", lat: -33.8624, lng: 151.0475 },
  "200040": { name: "Museum", lat: -33.8764, lng: 151.2110 },
  "200050": { name: "St James", lat: -33.8697, lng: 151.2124 },
  "201110": { name: "Kings Cross", lat: -33.8742, lng: 151.2241 },
  "207710": { name: "Hornsby", lat: -33.7032, lng: 151.1001 },
  "213810": { name: "Rhodes", lat: -33.8329, lng: 151.0858 },
  "214410": { name: "Auburn", lat: -33.8488, lng: 151.0326 },
  "216620": { name: "Cabramatta", lat: -33.8942, lng: 150.9397 },
  "217010": { name: "Liverpool", lat: -33.9201, lng: 150.9254 },
};

function getColor(delay) {
  if (delay === null) return "#57534e"
  if (delay <= 0.5) return "#22c55e"
  if (delay <= 2) return "#eab308"
  return "#ef4444"
}

export default function StationMap({ stationStats, selectedStation, onStationSelect }) {
    const mapRef = useRef(null)
    const mapInstanceRef = useRef(null)
    const markersRef = useRef({})
    const previousSelectedRef = useRef(null)
    const isMarkerClickRef = useRef(false)

    useEffect(() => {
      if (!mapInstanceRef.current || !selectedStation) return
      
      if (isMarkerClickRef.current) {
        isMarkerClickRef.current = false
        return
      }
      
      const station = STATION_COORDS[selectedStation.id]
      if (station) {
        mapInstanceRef.current.flyTo([station.lat, station.lng], 14, {
          duration: 1.5,
          easeLinearity: 0.25
        })
      }
    }, [selectedStation])

    // Apply/remove glow effect on marker selection
    useEffect(() => {
      if (previousSelectedRef.current && markersRef.current[previousSelectedRef.current]) {
        markersRef.current[previousSelectedRef.current].getElement()?.classList.remove("current-station-marker")
      }
      
      if (selectedStation && markersRef.current[selectedStation.id]) {
        markersRef.current[selectedStation.id].getElement()?.classList.add("current-station-marker")
        previousSelectedRef.current = selectedStation.id
      }
    }, [selectedStation])

    // Initialise the map and create markers once — never re-runs on data updates.
    useEffect(() => {
      if (mapInstanceRef.current) return

      const map = L.map(mapRef.current).setView([-33.87, 151.05], 11)
      mapInstanceRef.current = map

      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; CARTO'
      }).addTo(map)

      Object.entries(STATION_COORDS).forEach(([stopId, station]) => {
        const marker = L.circleMarker([station.lat, station.lng], {
          radius: 8,
          color: getColor(null),
          fillColor: getColor(null),
          fillOpacity: 0.7
        })
        .bindPopup(`<div style="font-family: monospace; font-size: 0.75rem"><strong>${station.name}</strong><br/>Loading…</div>`)
        .on('click', () => {
          isMarkerClickRef.current = true
          onStationSelect({ id: stopId, name: station.name })
        })
        .addTo(map)

        markersRef.current[stopId] = marker
      })

      return () => {
        map.remove()
        mapInstanceRef.current = null
      }
    }, [onStationSelect])

    // Update marker styles and popups whenever stationStats refreshes.
    // Runs independently of map init — never tears down the map.
    useEffect(() => {
      Object.entries(markersRef.current).forEach(([stopId, marker]) => {
        const stats = stationStats[stopId]
        const delay = stats?.avg_delay ?? null
        const trips = stats?.total_trips ?? 0
        const station = STATION_COORDS[stopId]

        marker.setStyle({
          radius: Math.max(8, Math.min(24, trips / 50)),
          color: getColor(delay),
          fillColor: getColor(delay),
        })
        marker.setPopupContent(`
          <div style="font-family: monospace; font-size: 0.75rem; color: var(--color-text)">
            <strong>${station.name}</strong><br/>
            Avg delay: ${delay !== null ? `${delay}m` : "no data"}<br/>
            Trips recorded: ${trips}<br/>
            Worst line: ${stats?.worst_line ?? "—"}
          </div>
        `)
      })
    }, [stationStats])

    return <div ref={mapRef} style={{ height: "100%", width: "100%" }} />
}