import { useState } from "react";
import HotelCard from "../components/HotelCard";

const MODEL_LABELS = { phobert: "PhoBERT", llama: "LLaMA", cnn_lstm: "CNN-LSTM", random_forest: "Random Forest", logistic: "Logistic" };

const ASPECTS_DEF = [
  { label: "Phòng ốc",  posKey: "room_positive_pct" },
  { label: "Nhân viên", posKey: "staff_positive_pct" },
  { label: "Vị trí",    posKey: "location_positive_pct" },
  { label: "Ăn uống",   posKey: "food_positive_pct" },
  { label: "Giá cả",    posKey: "price_positive_pct" },
  { label: "Tổng thể",  posKey: "general_positive_pct" },
];

function MiniAspectBar({ label, pct }) {
  const color = pct >= 75 ? "#4ade80" : pct >= 50 ? "#fbbf24" : "#f87171";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
      <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 56, textAlign: "right", flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, background: "rgba(255,255,255,0.08)", borderRadius: 99, height: 4 }}>
        <div style={{ height: 4, borderRadius: 99, background: color, width: `${pct}%`, transition: "width 0.4s" }} />
      </div>
      <span style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", width: 28, flexShrink: 0 }}>{pct}%</span>
    </div>
  );
}

function MultiModelCard({ hotelName, modelNames, rawResults, isTop, onSelectModel }) {
  const modelData = modelNames.map(m => {
    const d = rawResults.find(r => r.multi_model)?.models?.[m];
    const l = Array.isArray(d) ? d : (d?.results || []);
    const h = l.find(x => (x.name || x.hotel_name) === hotelName);
    const scores = h?.scores || h || {};
    return { model: m, hotel: h, scores, overall: Math.round(h?.match_score || scores?.overall_score || 0), total: scores.total_analyzed || h?.total || 0 };
  });
  const maxScore = Math.max(...modelData.map(d => d.overall));

  return (
    <div style={{
      background: isTop ? "rgba(124,58,237,0.08)" : "rgba(255,255,255,0.03)",
      border: isTop ? "1px solid rgba(124,58,237,0.4)" : "1px solid rgba(255,255,255,0.07)",
      borderRadius: 16, padding: 20, marginBottom: 16,
    }}>
      {isTop && <span style={{ background: "linear-gradient(135deg, #7c3aed, #4f46e5)", color: "#fff", fontSize: 11, padding: "3px 10px", borderRadius: 99, fontWeight: 600, display: "inline-block", marginBottom: 12 }}>🏆 Phù hợp nhất</span>}
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: "rgba(124,58,237,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>🏨</div>
        <div>
          <p style={{ color: "#fff", fontWeight: 600, fontSize: 14, margin: 0 }}>{hotelName}</p>
          <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 11, margin: "2px 0 0" }}>Ấn vào model để xem chi tiết</p>
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        {modelData.map(({ model, hotel, scores, overall, total }) => {
          const isBest = overall === maxScore && overall > 0;
          const scoreColor = overall >= 75 ? "#4ade80" : overall >= 50 ? "#fbbf24" : overall > 0 ? "#f87171" : "rgba(255,255,255,0.25)";
          return (
            <button key={model} onClick={() => hotel && onSelectModel(hotel, model)} disabled={!hotel}
              style={{
                minWidth: 140, flex: "1 1 140px", border: isBest ? "1px solid rgba(124,58,237,0.5)" : "1px solid rgba(255,255,255,0.08)",
                borderRadius: 12, padding: 12, textAlign: "left", cursor: hotel ? "pointer" : "not-allowed",
                background: isBest ? "rgba(124,58,237,0.15)" : "rgba(255,255,255,0.04)",
                opacity: hotel ? 1 : 0.35, transition: "all 0.2s",
              }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ color: "#a78bfa", fontSize: 11, fontWeight: 700 }}>{MODEL_LABELS[model] || model}</span>
                {isBest && <span style={{ fontSize: 12 }}>⭐</span>}
              </div>
              {hotel ? (
                <>
                  <div style={{ color: scoreColor, fontSize: 22, fontWeight: 800, marginBottom: 2 }}>{overall}%</div>
                  <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 10, marginBottom: 8 }}>{total} reviews</div>
                  {ASPECTS_DEF.map(a => <MiniAspectBar key={a.label} label={a.label} pct={Math.round(scores[a.posKey] || 0)} />)}
                </>
              ) : (
                <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 11, marginTop: 4 }}>Không có dữ liệu</div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const bgImage   = { position: "fixed", inset: 0, zIndex: 0, backgroundImage: "url('https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=1600&q=80')", backgroundSize: "cover", backgroundPosition: "center", filter: "brightness(0.12) saturate(0.6)" };
const bgOverlay = { position: "fixed", inset: 0, zIndex: 1, background: "linear-gradient(to bottom, rgba(15,12,41,0.85) 0%, rgba(15,12,41,0.75) 100%)" };
const pageStyle = { minHeight: "100vh", background: "#0f0c29", fontFamily: "'Segoe UI', system-ui, sans-serif", position: "relative" };


function AuthButton({ auth }) {
  if (auth.loading) return null;
  if (auth.user) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {auth.user.avatar && (
          <img src={auth.user.avatar} style={{ width: 30, height: 30, borderRadius: "50%", border: "2px solid rgba(167,139,250,0.5)" }} alt="avatar" />
        )}
        <span style={{ color: "rgba(255,255,255,0.7)", fontSize: 13 }}>{auth.user.name?.split(" ").pop()}</span>
        <button onClick={auth.logout} style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 99, padding: "5px 14px", color: "rgba(255,255,255,0.6)", fontSize: 12, cursor: "pointer" }}>
          Đăng xuất
        </button>
      </div>
    );
  }
  return (
    <button onClick={auth.login} style={{ background: "linear-gradient(135deg, #7c3aed, #4f46e5)", border: "none", borderRadius: 99, padding: "7px 18px", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer", boxShadow: "0 4px 12px rgba(124,58,237,0.35)", display: "flex", alignItems: "center", gap: 8 }}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#fff"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#fff" opacity=".8"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#fff" opacity=".6"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#fff" opacity=".7"/></svg>
      Đăng nhập
    </button>
  );
}

export default function Results({ results, meta, onSelect, onBack, auth = {} }) {
  const rawResults   = results?.results || [];
  const isMultiModel = rawResults.some(r => r.multi_model);
  const hotels       = isMultiModel ? [] : (results?.hotels || rawResults);
  const modelNames   = isMultiModel ? Object.keys(rawResults.find(r => r.multi_model)?.models || {}) : [];
  const allHotelNames = isMultiModel ? [...new Set(
    modelNames.flatMap(m => {
      const d = rawResults.find(r => r.multi_model)?.models?.[m];
      const l = Array.isArray(d) ? d : (d?.results || []);
      return l.map(h => h.name || h.hotel_name || "").filter(Boolean);
    })
  )] : [];

  return (
    <div style={pageStyle}>
      <div style={bgImage} />
      <div style={bgOverlay} />
      <nav style={{ padding: "14px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(255,255,255,0.06)", position: "relative", zIndex: 2 }}>
        <div onClick={onBack} style={{ display: "flex", alignItems: "center", gap: 8, color: "#fff", fontWeight: 700, cursor: "pointer", fontSize: 16 }}>
          <img src="/logo.png" style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover" }} alt="logo" /> HotelSense
        </div>
        <AuthButton auth={auth} />
      </nav>

      {/* Filter bar */}
      <div style={{ padding: "10px 28px", position: "relative", zIndex: 2, borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        {meta?.city && <span style={{ background: "rgba(124,58,237,0.2)", color: "#c4b5fd", fontSize: 12, padding: "3px 10px", borderRadius: 99, border: "1px solid rgba(124,58,237,0.3)" }}>📍 {meta.city}{meta.district ? ` — ${meta.district}` : ""}</span>}
        {isMultiModel && <span style={{ background: "rgba(124,58,237,0.2)", color: "#c4b5fd", fontSize: 12, padding: "3px 10px", borderRadius: 99, border: "1px solid rgba(124,58,237,0.3)" }}>So sánh {modelNames.length} model</span>}
        {meta?.aspects?.map(a => <span key={a} style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.6)", fontSize: 12, padding: "3px 10px", borderRadius: 99 }}>{a}</span>)}
      </div>

      <div style={{ maxWidth: 720, margin: "0 auto", padding: "24px 20px", position: "relative", zIndex: 2 }}>
        <div style={{ marginBottom: 20 }}>
          <p style={{ color: "#fff", fontWeight: 700, fontSize: 16, margin: "0 0 4px" }}>
            {isMultiModel ? allHotelNames.length : hotels.length} khách sạn phù hợp
          </p>
          <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, margin: 0 }}>
            {isMultiModel ? "Ấn vào ô model để xem phân tích chi tiết" : "Sắp xếp theo độ phù hợp với yêu cầu"}
          </p>
        </div>

        {isMultiModel ? (
          allHotelNames.map((name, i) => (
            <MultiModelCard key={name} hotelName={name} modelNames={modelNames} rawResults={rawResults} isTop={i === 0}
              onSelectModel={(hotel, model) => onSelect({ ...hotel, _model: model })} />
          ))
        ) : hotels.length === 0 ? (
          <div style={{ textAlign: "center", padding: "64px 0", color: "rgba(255,255,255,0.3)" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
            <p style={{ fontSize: 15, margin: "0 0 8px" }}>Không tìm thấy khách sạn phù hợp</p>
            <p style={{ fontSize: 13 }}>Thử thay đổi bộ lọc hoặc chọn thành phố khác</p>
          </div>
        ) : (
          hotels.map((hotel, i) => (
            <HotelCard key={hotel.id || hotel.url || i} hotel={hotel} isTop={i === 0} onClick={() => onSelect(hotel)} />
          ))
        )}
      </div>
    </div>
  );
}