// RadarChart.jsx — Radar chart 6 aspects bằng SVG thuần

export default function RadarChart({ data = [], dark = false }) {
  if (!data.length) return null;

  const cx = 90, cy = 90, r = 65;
  const n  = data.length;

  function getPoint(i, value) {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const dist  = (value / 100) * r;
    return {
      x: cx + dist * Math.cos(angle),
      y: cy + dist * Math.sin(angle),
    };
  }

  function getLabelPoint(i) {
    const angle  = (Math.PI * 2 * i) / n - Math.PI / 2;
    const dist   = r + 16;
    return {
      x: cx + dist * Math.cos(angle),
      y: cy + dist * Math.sin(angle),
    };
  }

  // Vẽ lưới
  const gridLevels = [25, 50, 75, 100];
  const gridPolygons = gridLevels.map(level => {
    const pts = data.map((_, i) => {
      const p = getPoint(i, level);
      return `${p.x},${p.y}`;
    });
    return pts.join(" ");
  });

  // Vẽ dữ liệu
  const dataPoints = data.map((d, i) => getPoint(i, d.value));
  const dataPolygon = dataPoints.map(p => `${p.x},${p.y}`).join(" ");

  return (
    <svg viewBox="0 0 180 180" className="w-full max-w-[180px] mx-auto">
      {/* Lưới */}
      {gridPolygons.map((pts, gi) => (
        <polygon key={gi} points={pts}
          fill="none" stroke={dark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'} strokeWidth="0.5" />
      ))}

      {/* Trục */}
      {data.map((_, i) => {
        const outer = getPoint(i, 100);
        return <line key={i} x1={cx} y1={cy} x2={outer.x} y2={outer.y}
          stroke={dark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'} strokeWidth="0.5" />;
      })}

      {/* Data polygon */}
      <polygon points={dataPolygon}
        fill="rgba(99,102,241,0.15)" stroke="#6366F1" strokeWidth="1.5" />

      {/* Data points */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill="#6366F1" />
      ))}

      {/* Labels */}
      {data.map((d, i) => {
        const lp = getLabelPoint(i);
        return (
          <text key={i} x={lp.x} y={lp.y}
            textAnchor="middle" dominantBaseline="central"
fontSize="8" fill={dark ? "rgba(255,255,255,0.5)" : "#6B7280"}>
            {d.label}
          </text>
        );
      })}
    </svg>
  );
}