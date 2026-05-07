import { useState, useEffect } from "react";
import { getHotelReviews } from "../api";
import RadarChart  from "../components/RadarChart";
import CommentList from "../components/CommentList";

const ASPECTS = [
  { key: "Room_Facilities", label: "Phòng ốc",  posKey: "room_positive_pct",     negKey: "room_negative_pct" },
  { key: "Service_Staff",   label: "Nhân viên",  posKey: "staff_positive_pct",    negKey: "staff_negative_pct" },
  { key: "Location",        label: "Vị trí",     posKey: "location_positive_pct", negKey: "location_negative_pct" },
  { key: "Food_Beverage",   label: "Ăn uống",    posKey: "food_positive_pct",     negKey: "food_negative_pct" },
  { key: "Price_Value",     label: "Giá cả",     posKey: "price_positive_pct",    negKey: "price_negative_pct" },
  { key: "General",         label: "Tổng thể",   posKey: "general_positive_pct",  negKey: "general_negative_pct" },
];

function pctColor(pct) {
  if (pct >= 75) return "#4ade80";
  if (pct >= 50) return "#fbbf24";
  return "#f87171";
}

export default function Detail({ hotel, onBack, onGoHome }) {
  const [allReviews,   setAllReviews]   = useState(hotel?.reviews || []);
  const [filterAspect, setFilterAspect] = useState("");
  const [filterSent,   setFilterSent]   = useState(null);
  const [reviews,      setReviews]      = useState(hotel?.reviews || []);
  const [loading,      setLoading]      = useState(false);

  const scores = hotel?.scores || hotel || {};

  useEffect(() => {
    if (hotel?.id && !hotel.reviews?.length) {
      // DB mode: load all reviews mot lan, roi filter local
      setLoading(true);
      getHotelReviews(hotel.id, { limit: 200 })
        .then(r => {
          const list = r.reviews || [];
          setAllReviews(list);
          setReviews(list);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    } else {
      const list = hotel?.reviews || [];
      setAllReviews(list);
      setReviews(list);
    }
  }, [hotel]);

  const ASPECT_KEYS = {
    Room_Facilities: "room_facilities", Service_Staff: "service_staff",
    Location: "location", Food_Beverage: "food_beverage",
    Price_Value: "price_value", General: "general",
  };

  function handleFilter(aspect, sentiment) {
    setFilterAspect(aspect);
    setFilterSent(sentiment);

    // Filter local cho ca 2 mode - mượt, không reload
    let filtered = allReviews;
    if (aspect) {
      const key = ASPECT_KEYS[aspect] || aspect.toLowerCase();
      filtered = filtered.filter(r => {
        const val = r[key];
        if (sentiment !== null) return val === sentiment;
        return val && val !== 0;
      });
    } else if (sentiment !== null) {
      filtered = filtered.filter(r =>
        Object.values(ASPECT_KEYS).some(k => r[k] === sentiment)
      );
    }
    setReviews(filtered);
  }

  const radarData = ASPECTS.map(a => ({ label: a.label, value: Math.round(scores[a.posKey] || 0) }));
  const pros = ASPECTS.filter(a => (scores[a.posKey] || 0) >= 75).map(a => a.label);
  const cons = ASPECTS.filter(a => (scores[a.posKey] || 0) < 50).map(a => a.label);
  const matchScore = Math.round(hotel?.match_score || scores?.overall_score || 0);
  const scoreColor = matchScore >= 85 ? "#4ade80" : matchScore >= 70 ? "#fbbf24" : "#94a3b8";

  const page = { minHeight: "100vh", background: "#0f0c29", fontFamily: "'Segoe UI', system-ui, sans-serif", position: "relative" };

  return (
    <div style={page}>
      <div style={{ position: "fixed", inset: 0, zIndex: 0, backgroundImage: "url('https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=1600&q=80')", backgroundSize: "cover", backgroundPosition: "center", filter: "brightness(0.12) saturate(0.6)" }} />
      <div style={{ position: "fixed", inset: 0, zIndex: 1, background: "linear-gradient(to bottom, rgba(15,12,41,0.9) 0%, rgba(15,12,41,0.8) 100%)" }} />
      {/* Navbar */}
      <nav style={{ position: "relative", zIndex: 2, padding: "14px 28px", display: "flex", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div onClick={onGoHome} style={{ display: "flex", alignItems: "center", gap: 8, color: "#fff", fontWeight: 700, fontSize: 16, cursor: "pointer" }}>
          <img src="/logo.png" style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover" }} alt="logo" /> HotelSense
        </div>
      </nav>

      {/* Hotel header */}
      <div style={{ position: "relative", zIndex: 2, padding: "28px 28px 24px", borderBottom: "1px solid rgba(255,255,255,0.06)", maxWidth: 760, margin: "0 auto", width: "100%" }}>
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start", marginBottom: 20 }}>
          <div style={{ width: 60, height: 60, borderRadius: 14, background: "rgba(124,58,237,0.25)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26, flexShrink: 0, border: "1px solid rgba(124,58,237,0.3)" }}>🏨</div>
          <div style={{ flex: 1 }}>
            <h1 style={{ color: "#fff", fontSize: 20, fontWeight: 800, margin: "0 0 6px", letterSpacing: "-0.5px" }}>{hotel?.name || "Khách sạn"}</h1>
            {(hotel?.address || hotel?.city) && (
              <p style={{ color: "rgba(255,255,255,0.45)", fontSize: 13, margin: "0 0 10px" }}>📍 {hotel?.address || hotel?.city}</p>
            )}
            <span style={{ background: `${scoreColor}20`, color: scoreColor, fontSize: 13, padding: "4px 12px", borderRadius: 99, fontWeight: 700, border: `1px solid ${scoreColor}40` }}>
              Phù hợp {matchScore}%
            </span>
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: hotel?.stars > 0 ? "1fr 1fr 1fr" : "1fr 1fr", gap: 12 }}>
          {[
            { value: Math.round(scores?.overall_score || 0), label: "Điểm ABSA", color: "#a78bfa" },
            { value: scores?.total_analyzed || hotel?.total || hotel?.total_reviews || 0, label: "Reviews", color: "#60a5fa" },
            ...(hotel?.stars > 0 ? [{ value: `${hotel.stars}★`, label: "Sao", color: "#fbbf24" }] : []),
          ].map((s, i) => (
            <div key={i} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 14, padding: "16px 0", textAlign: "center" }}>
              <div style={{ color: s.color, fontSize: 28, fontWeight: 800, lineHeight: 1 }}>{s.value}</div>
              <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, marginTop: 6 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ maxWidth: 760, margin: "0 auto", padding: "24px 28px", position: "relative", zIndex: 2 }}>

        {/* Radar + bars */}
        <p style={{ color: "#fff", fontWeight: 700, fontSize: 15, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          📊 Phân tích 6 khía cạnh
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 16, padding: 16 }}>
            <RadarChart data={radarData} dark={true} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 10 }}>
            {ASPECTS.map(a => {
              const pct = Math.round(scores[a.posKey] || 0);
              const color = pctColor(pct);
              return (
                <div key={a.key} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ color: "rgba(255,255,255,0.55)", fontSize: 12, width: 68, flexShrink: 0 }}>{a.label}</span>
                  <div style={{ flex: 1, height: 6, background: "rgba(255,255,255,0.08)", borderRadius: 99 }}>
                    <div style={{ height: 6, borderRadius: 99, background: color, width: `${pct}%`, transition: "width 0.5s" }} />
                  </div>
                  <span style={{ color, fontSize: 12, fontWeight: 700, width: 36, textAlign: "right" }}>{pct}%</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Pros / Cons */}
        {(pros.length > 0 || cons.length > 0) && (
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 16, padding: 18, marginBottom: 20 }}>
            {pros.length > 0 && (
              <div style={{ marginBottom: cons.length > 0 ? 14 : 0 }}>
                <p style={{ color: "#4ade80", fontSize: 12, fontWeight: 700, marginBottom: 8 }}>✅ Điểm mạnh</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {pros.map(p => <span key={p} style={{ background: "rgba(74,222,128,0.12)", color: "#4ade80", fontSize: 11, padding: "3px 10px", borderRadius: 99, border: "1px solid rgba(74,222,128,0.2)" }}>{p}</span>)}
                </div>
              </div>
            )}
            {cons.length > 0 && (
              <div>
                <p style={{ color: "#f87171", fontSize: 12, fontWeight: 700, marginBottom: 8 }}>⚠️ Hạn chế</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {cons.map(c => <span key={c} style={{ background: "rgba(248,113,113,0.12)", color: "#f87171", fontSize: 11, padding: "3px 10px", borderRadius: 99, border: "1px solid rgba(248,113,113,0.2)" }}>{c}</span>)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Comments */}
        <CommentList
          reviews={reviews}
          loading={loading}
          aspects={ASPECTS}
          onFilter={handleFilter}
          activeAspect={filterAspect}
          activeSent={filterSent}
        />
      </div>
    </div>
  );
}