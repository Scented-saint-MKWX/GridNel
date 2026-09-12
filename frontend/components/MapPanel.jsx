'use client';

import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';

export default function MapPanel({ markers = [], lines = [] }) {
  const ref = useRef(null);
  useEffect(() => {
    mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || 'pk.test';
    const map = new mapboxgl.Map({
      container: ref.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [77.209, 28.6139],
      zoom: 11,
    });
    markers.forEach((m) => {
      new mapboxgl.Marker({ color: m.flash ? 'red' : 'blue' })
        .setLngLat([m.lon, m.lat])
        .setPopup(new mapboxgl.Popup().setText(`${m.label}`))
        .addTo(map);
    });
    lines.forEach((l, i) => {
      map.on('load', () => {
        map.addSource(`line-${i}`, {
          type: 'geojson',
          data: { type: 'Feature', geometry: { type: 'LineString', coordinates: l.coords.map((p) => [p[1], p[0]]) } }
        });
        map.addLayer({
          id: `line-${i}`,
          type: 'line',
          source: `line-${i}`,
          paint: { 'line-width': 4, 'line-color': l.dashed ? '#888' : '#0d6efd', 'line-dasharray': l.dashed ? [2,2] : [1,0] }
        });
      });
    });
    return () => map.remove();
  }, [markers, lines]);

  return <div ref={ref} style={{ width: '100%', height: 420 }} />;
}
