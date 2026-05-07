import { useState, useEffect } from "react";
import { searchHotels, analyzeUrls, getStats } from "../api";

const ASPECTS = [
  { key: "Room_Facilities", label: "Phòng ốc",  icon: "🛏" },
  { key: "Service_Staff",   label: "Nhân viên",  icon: "👤" },
  { key: "Location",        label: "Vị trí",     icon: "📍" },
  { key: "Food_Beverage",   label: "Ăn uống",    icon: "🍽" },
  { key: "Price_Value",     label: "Giá cả",     icon: "💰" },
  { key: "General",         label: "Tổng thể",   icon: "⭐" },
];

const DISTRICT_MAP = {
  "Ho Chi Minh City": [
    { label: "Bình Thạnh", value: "Bình Thạnh" },
    { label: "Quận 1",     value: "District 1" },
    { label: "Quận 10",    value: "District 10" },
    { label: "Quận 2",     value: "District 2" },
    { label: "Quận 4",     value: "District 4" },
    { label: "Quận 7",     value: "District 7" },
    { label: "Tân Bình",   value: "Tân Bình" },
  ],
  "Hanoi": [
    { label: "Ba Đình",   value: "Ba Đình" },
    { label: "Cầu Giấy",  value: "Cầu Giấy" },
    { label: "Hoàn Kiếm", value: "Hoàn Kiếm" },
    { label: "Tây Hồ",    value: "Tây Hồ" },
    { label: "Đống Đa",   value: "Đống Đa" },
  ],
  "Da Nang": [
    { label: "Hải Châu",     value: "Hải Châu" },
    { label: "Ngũ Hành Sơn", value: "Ngũ Hành Sơn" },
    { label: "Sơn Trà",      value: "Sơn Trà" },
    { label: "Thanh Khê",    value: "Thanh Khê" },
  ],
};

const S = {
  page: { minHeight: "100vh", background: "#0f0c29", display: "flex", flexDirection: "column", fontFamily: "'Segoe UI', system-ui, sans-serif", position: "relative" },
  nav: { padding: "16px 32px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(255,255,255,0.06)" },
  logo: { display: "flex", alignItems: "center", gap: 10 },
  logoText: { color: "#fff", fontWeight: 700, fontSize: 18, letterSpacing: "-0.5px" },
  aiBadge: { background: "rgba(139,92,246,0.3)", color: "#c4b5fd", fontSize: 10, padding: "2px 8px", borderRadius: 99, border: "1px solid rgba(139,92,246,0.4)", marginLeft: 4 },
  hero: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "48px 24px" },
  h1: { color: "#fff", fontSize: 36, fontWeight: 800, letterSpacing: "-1px", margin: "0 0 12px", lineHeight: 1.2, textAlign: "center" },
  gradient: { background: "linear-gradient(90deg, #a78bfa, #60a5fa)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" },
  subtitle: { color: "rgba(255,255,255,0.5)", fontSize: 15, margin: "0 0 40px", textAlign: "center" },
  tabs: { display: "flex", background: "rgba(255,255,255,0.06)", borderRadius: 99, padding: 4, marginBottom: 28, border: "1px solid rgba(255,255,255,0.08)" },
  card: { width: "100%", maxWidth: 600, background: "rgba(255,255,255,0.04)", backdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20, padding: 28, boxShadow: "0 24px 64px rgba(0,0,0,0.4)" },
  label: { color: "rgba(255,255,255,0.45)", fontSize: 12, marginBottom: 8, display: "block" },
  select: { flex: 1, background: "#1e1b4b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: "9px 12px", color: "#fff", fontSize: 13, outline: "none", cursor: "pointer", colorScheme: "dark" },
  input: { flex: 1, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: "8px 12px", color: "#fff", fontSize: 12, outline: "none", minWidth: 0 },
  footer: { textAlign: "center", padding: 16, color: "rgba(255,255,255,0.2)", fontSize: 12 },
};

function AspectBtn({ aspect, selected, onClick }) {
  return (
    <button onClick={onClick} style={{
      padding: "6px 14px", borderRadius: 99, fontSize: 12, cursor: "pointer", transition: "all 0.2s", fontWeight: 500,
      background: selected ? "linear-gradient(135deg, #7c3aed, #4f46e5)" : "rgba(255,255,255,0.06)",
      color: selected ? "#fff" : "rgba(255,255,255,0.55)",
      border: selected ? "1px solid rgba(124,58,237,0.5)" : "1px solid rgba(255,255,255,0.1)",
      boxShadow: selected ? "0 4px 12px rgba(124,58,237,0.3)" : "none",
    }}>
      {aspect.icon} {aspect.label}
    </button>
  );
}

export default function Home({ onSearch }) {
  const [mode,       setMode]       = useState("db");
  const [city,       setCity]       = useState("");
  const [district,   setDistrict]   = useState("");
  const [aspects,    setAspects]    = useState([]);
  const [urls,       setUrls]       = useState([""]);
  const [maxReviews, setMaxReviews] = useState(50);
  const [models,     setModels]     = useState(["phobert"]);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState("");
  const [stats,      setStats]      = useState(null);

  useEffect(() => { getStats().then(r => setStats(r.stats)).catch(() => {}); }, []);

  const districts = city ? (DISTRICT_MAP[city] || []) : [];

  function toggleAspect(key) {
    setAspects(prev => prev.includes(key) ? prev.filter(a => a !== key) : [...prev, key]);
  }

  function toggleModel(val) {
    setModels(prev => prev.includes(val) ? (prev.length > 1 ? prev.filter(x => x !== val) : prev) : [...prev, val]);
  }

  async function handleSearch() {
    if (mode === "db" && !city) { setError("Vui lòng chọn thành phố"); return; }
    setError(""); setLoading(true);
    try {
      let data, meta;
      if (mode === "db") {
        data = await searchHotels({ city, district, priorityAspects: aspects });
        meta = { mode: "db", city, district, aspects };
      } else {
        const filteredUrls = urls.filter(u => u.trim());
        if (!filteredUrls.length) { setError("Vui lòng nhập ít nhất 1 URL"); setLoading(false); return; }
        data = await analyzeUrls({ urls: filteredUrls, maxReviews, models, priorityAspects: aspects });
        meta = { mode: "url", aspects, models };
      }
      onSearch(data, meta);
    } catch (e) {
      setError("Lỗi kết nối API: " + e.message);
    } finally { setLoading(false); }
  }

  return (
    <div style={S.page}>
      {/* Background image */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0,
        backgroundImage: "url('https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=1600&q=80')",
        backgroundSize: "cover", backgroundPosition: "center",
        filter: "brightness(0.18) saturate(0.8)",
      }} />
      {/* Gradient overlay */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 1,
        background: "linear-gradient(to bottom, rgba(15,12,41,0.6) 0%, rgba(15,12,41,0.3) 40%, rgba(15,12,41,0.85) 100%)",
      }} />
      <nav style={{ ...S.nav, position: "relative", zIndex: 2 }}>
        <div style={S.logo}>
          <img src="/logo.png" style={{ width: 34, height: 34, borderRadius: "50%", objectFit: "cover", border: "1.5px solid rgba(255,255,255,0.15)" }} alt="logo" />
          <span style={S.logoText}>HotelSense</span>

        </div>
        {stats && (
          <div style={{ display: "flex", gap: 24 }}>
            {Object.entries(stats.by_city || {}).map(([c, cnt]) => (
              <div key={c} style={{ textAlign: "center" }}>
                <div style={{ color: "#a78bfa", fontWeight: 700, fontSize: 15 }}>{cnt}</div>
                <div style={{ color: "rgba(255,255,255,0.35)", fontSize: 11 }}>KS {c}</div>
              </div>
            ))}
          </div>
        )}
      </nav>

      <div style={{ ...S.hero, position: "relative", zIndex: 2 }}>
        <h1 style={S.h1}>
          Tìm khách sạn<br />
          <span style={S.gradient}>phù hợp nhất với bạn</span>
        </h1>
        <p style={S.subtitle}>Phân tích hàng nghìn đánh giá thực bằng AI — không chỉ điểm sao</p>

        {/* Mode tabs */}
        <div style={S.tabs}>
          {[{ id: "db", label: "🗄 Tìm từ database" }, { id: "url", label: "🔗 Phân tích theo link" }].map(m => (
            <button key={m.id} onClick={() => setMode(m.id)} style={{
              padding: "8px 20px", borderRadius: 99, border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, transition: "all 0.2s",
              background: mode === m.id ? "linear-gradient(135deg, #7c3aed, #4f46e5)" : "transparent",
              color: mode === m.id ? "#fff" : "rgba(255,255,255,0.5)",
              boxShadow: mode === m.id ? "0 4px 15px rgba(124,58,237,0.4)" : "none",
            }}>{m.label}</button>
          ))}
        </div>

        {/* Card */}
        <div style={S.card}>
          {mode === "db" && (
            <>
              <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
                <select value={city} onChange={e => { setCity(e.target.value); setDistrict(""); }} style={S.select}>
                  <option value="">📍 Chọn thành phố</option>
                  <option value="Ho Chi Minh City">TP. Hồ Chí Minh</option>
                  <option value="Hanoi">Hà Nội</option>
                  <option value="Da Nang">Đà Nẵng</option>
                </select>
                <select value={district} onChange={e => setDistrict(e.target.value)} disabled={!districts.length} style={{ ...S.select, opacity: districts.length ? 1 : 0.4 }}>
                  <option value="">Tất cả khu vực</option>
                  {districts.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
                </select>
              </div>
              <span style={S.label}>Khía cạnh quan trọng với bạn:</span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {ASPECTS.map(a => <AspectBtn key={a.key} aspect={a} selected={aspects.includes(a.key)} onClick={() => toggleAspect(a.key)} />)}
              </div>
            </>
          )}

          {mode === "url" && (
            <>
              <span style={S.label}>Paste link Traveloka khách sạn:</span>
              {urls.map((u, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
                  <span style={{ background: "rgba(124,58,237,0.2)", color: "#a78bfa", fontSize: 11, padding: "4px 10px", borderRadius: 99, whiteSpace: "nowrap", border: "1px solid rgba(124,58,237,0.3)" }}>Link {i+1}</span>
                  <input value={u} onChange={e => setUrls(prev => prev.map((v, j) => j === i ? e.target.value : v))}
                    placeholder="https://www.traveloka.com/vi-vn/hotel/..." style={S.input} />
                  {urls.length > 1 && (
                    <button onClick={() => setUrls(prev => prev.filter((_, j) => j !== i))}
                      style={{ color: "rgba(255,100,100,0.7)", background: "none", border: "none", cursor: "pointer", fontSize: 16 }}>✕</button>
                  )}
                </div>
              ))}
              <button onClick={() => setUrls(prev => [...prev, ""])} style={{ color: "#a78bfa", background: "none", border: "none", cursor: "pointer", fontSize: 12, marginBottom: 16, padding: 0 }}>+ Thêm link</button>

              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                <span style={{ color: "rgba(255,255,255,0.45)", fontSize: 12, whiteSpace: "nowrap" }}>Số comment:</span>
                <input type="range" min="10" max="200" step="10" value={maxReviews} onChange={e => setMaxReviews(Number(e.target.value))} style={{ flex: 1, accentColor: "#7c3aed" }} />
                <input type="number" min="10" max="500" value={maxReviews} onChange={e => setMaxReviews(Math.max(10, Math.min(500, Number(e.target.value) || 10)))}
                  style={{ width: 52, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "4px 6px", color: "#fff", fontSize: 12, textAlign: "center", outline: "none" }} />
              </div>

              <span style={S.label}>Mô hình AI <span style={{ color: "#a78bfa" }}>({models.length} đã chọn)</span> — chọn nhiều để so sánh:</span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16 }}>
                {[
                  { value: "phobert", label: "PhoBERT" }, { value: "llama", label: "LLaMA" },
                  { value: "cnn_lstm", label: "CNN-LSTM" }, { value: "random_forest", label: "Random Forest" },
                  { value: "logistic", label: "Logistic" },
                ].map(m => (
                  <button key={m.value} onClick={() => toggleModel(m.value)} style={{
                    padding: "5px 12px", borderRadius: 99, fontSize: 11, cursor: "pointer", fontWeight: 600, transition: "all 0.2s",
                    background: models.includes(m.value) ? "linear-gradient(135deg, #7c3aed, #4f46e5)" : "rgba(255,255,255,0.06)",
                    color: models.includes(m.value) ? "#fff" : "rgba(255,255,255,0.5)",
                    border: models.includes(m.value) ? "1px solid rgba(124,58,237,0.5)" : "1px solid rgba(255,255,255,0.1)",
                  }}>{m.label}{models.includes(m.value) && models.length > 1 ? " ✓" : ""}</button>
                ))}
              </div>
              {models.length > 1 && <p style={{ color: "#fbbf24", fontSize: 11, marginBottom: 12 }}>⚠ {models.length} model — kết quả hiển thị song song</p>}

              <span style={S.label}>Khía cạnh quan trọng với bạn:</span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {ASPECTS.map(a => <AspectBtn key={a.key} aspect={a} selected={aspects.includes(a.key)} onClick={() => toggleAspect(a.key)} />)}
              </div>
            </>
          )}

          {error && <p style={{ color: "#f87171", fontSize: 12, marginTop: 12 }}>{error}</p>}

          <button onClick={handleSearch} disabled={loading} style={{
            width: "100%", marginTop: 20, padding: "13px 0", borderRadius: 12, border: "none",
            cursor: loading ? "not-allowed" : "pointer",
            background: loading ? "rgba(124,58,237,0.4)" : "linear-gradient(135deg, #7c3aed, #4f46e5)",
            color: "#fff", fontSize: 14, fontWeight: 700, letterSpacing: "0.3px",
            boxShadow: loading ? "none" : "0 8px 24px rgba(124,58,237,0.4)",
            transition: "all 0.2s",
          }}>
            {loading ? "⏳ Đang phân tích..." : "🔍 Tìm khách sạn phù hợp"}
          </button>
        </div>
      </div>

      <footer style={{ ...S.footer, position: "relative", zIndex: 2 }}>© {new Date().getFullYear()} HotelSense — AI Hotel Review Analyzer</footer>
    </div>
  );
}