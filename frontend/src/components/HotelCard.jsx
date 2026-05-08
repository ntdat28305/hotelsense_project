import { useState } from "react";
import { addBookmark, removeBookmark } from "../api";

export function HotelCard({ hotel, isTop, onClick, user }) {
  const [bookmarked, setBookmarked] = useState(false);
  const [bmLoading,  setBmLoading]  = useState(false);

  async function toggleBookmark(e) {
    e.stopPropagation();
    if (!user) return;
    setBmLoading(true);
    try {
      if (bookmarked) {
        await removeBookmark(hotel.id);
        setBookmarked(false);
      } else {
        await addBookmark(hotel);
        setBookmarked(true);
      }
    } catch {}
    finally { setBmLoading(false); }
  }
  const scores = hotel.scores || hotel;
  const aspects = [
    { label: "Phòng",    pct: Math.round(scores.room_positive_pct     || 0) },
    { label: "Nhân viên",pct: Math.round(scores.staff_positive_pct    || 0) },
    { label: "Vị trí",   pct: Math.round(scores.location_positive_pct || 0) },
    { label: "Ăn uống",  pct: Math.round(scores.food_positive_pct     || 0) },
    { label: "Giá cả",   pct: Math.round(scores.price_positive_pct    || 0) },
  ];
  const matchScore = Math.round(hotel.match_score || scores.overall_score || 0);
  const scoreColor = matchScore >= 85 ? "#4ade80" : matchScore >= 70 ? "#fbbf24" : "#94a3b8";

  return (
    <div onClick={onClick} style={{
      background: isTop ? "rgba(124,58,237,0.08)" : "rgba(255,255,255,0.03)",
      border: isTop ? "1px solid rgba(124,58,237,0.4)" : "1px solid rgba(255,255,255,0.07)",
      borderRadius: 16, padding: "18px 20px", marginBottom: 12, cursor: "pointer",
      transition: "all 0.2s", backdropFilter: "blur(10px)",
    }}
    onMouseEnter={e => e.currentTarget.style.background = isTop ? "rgba(124,58,237,0.14)" : "rgba(255,255,255,0.06)"}
    onMouseLeave={e => e.currentTarget.style.background = isTop ? "rgba(124,58,237,0.08)" : "rgba(255,255,255,0.03)"}
    >
      {isTop && (
        <div style={{ marginBottom: 10 }}>
          <span style={{ background: "linear-gradient(135deg, #7c3aed, #4f46e5)", color: "#fff", fontSize: 11, padding: "3px 10px", borderRadius: 99, fontWeight: 600 }}>
            🏆 Phù hợp nhất
          </span>
        </div>
      )}
      <div style={{ display: "flex", gap: 14, alignItems: "flex-start", marginBottom: 14 }}>
        <div style={{ width: 44, height: 44, borderRadius: 12, background: "rgba(124,58,237,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, flexShrink: 0 }}>🏨</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ color: "#fff", fontWeight: 600, fontSize: 14, margin: "0 0 4px", lineHeight: 1.3 }}>{hotel.name}</p>
          {(hotel.address || hotel.region || hotel.district || hotel.city) && (
            <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, margin: 0 }}>
              📍 {hotel.address || hotel.region || hotel.district || hotel.city}
            </p>
          )}
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div style={{ color: scoreColor, fontWeight: 800, fontSize: 26, lineHeight: 1 }}>{matchScore}%</div>
          <div style={{ color: "rgba(255,255,255,0.35)", fontSize: 11, marginTop: 2 }}>phù hợp</div>
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
        {aspects.map(a => {
          const bg = a.pct >= 75 ? "rgba(74,222,128,0.15)" : a.pct >= 50 ? "rgba(251,191,36,0.15)" : "rgba(248,113,113,0.15)";
          const color = a.pct >= 75 ? "#4ade80" : a.pct >= 50 ? "#fbbf24" : "#f87171";
          const mark = a.pct >= 75 ? "✓" : a.pct < 50 ? "✗" : "~";
          return (
            <span key={a.label} style={{ background: bg, color, fontSize: 11, padding: "3px 10px", borderRadius: 99, fontWeight: 600 }}>
              {a.label} {a.pct}% {mark}
            </span>
          );
        })}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ color: "rgba(255,255,255,0.3)", fontSize: 11 }}>
          💬 {hotel.total_analyzed || scores.total_analyzed || hotel.total || 0} reviews phân tích
        </span>
        <span style={{ color: "#a78bfa", fontSize: 12, fontWeight: 600 }}>Xem chi tiết →</span>
        {user && (
          <button onClick={toggleBookmark} disabled={bmLoading} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 18, opacity: bmLoading ? 0.5 : 1 }}>
            {bookmarked ? "🔖" : "🏷️"}
          </button>
        )}
      </div>
    </div>
  );
}

export default HotelCard;