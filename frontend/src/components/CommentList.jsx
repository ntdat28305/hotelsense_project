// CommentList.jsx — Danh sách comments đã gán nhãn ABSA

const LABEL_MAP = { 0: null, 1: "Negative", 2: "Positive" };

function AspectChip({ label, sentiment }) {
  const color = sentiment === 2
    ? "bg-green-100 text-green-700"
    : "bg-red-100 text-red-700";
  const icon  = sentiment === 2 ? "✓" : "✗";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>
      {label} {icon}
    </span>
  );
}

export default function CommentList({ reviews, loading, aspects, onFilter, activeAspect, activeSent }) {
  return (
    <div>
      <p className="text-sm font-medium text-gray-800 mb-3 flex items-center gap-2">
        💬 Comments đã được AI phân tích
      </p>

      {/* Filter buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => onFilter("", null)}
          className={`text-xs px-3 py-1 rounded-full border transition ${!activeAspect ? "bg-indigo-100 text-indigo-700 border-indigo-300" : "bg-white text-gray-500 border-gray-200"}`}>
          Tất cả
        </button>
        {aspects.map(a => (
          <button key={a.key}
            onClick={() => onFilter(a.key, null)}
            className={`text-xs px-3 py-1 rounded-full border transition ${activeAspect === a.key ? "bg-indigo-100 text-indigo-700 border-indigo-300" : "bg-white text-gray-500 border-gray-200"}`}>
            {a.label}
          </button>
        ))}
        <button
          onClick={() => onFilter(activeAspect, 1)}
          className={`text-xs px-3 py-1 rounded-full border transition ${activeSent === 1 ? "bg-red-100 text-red-700 border-red-300" : "bg-white text-gray-500 border-gray-200"}`}>
          Chỉ tiêu cực
        </button>
      </div>

      {/* Comments */}
      {loading ? (
        <div className="text-center py-8 text-gray-400 text-sm">⏳ Đang tải...</div>
      ) : reviews.length === 0 ? (
        <div className="text-center py-8 text-gray-400 text-sm">Không có comments</div>
      ) : (
        <>
          {reviews.map((r, i) => {
            const labels = aspects
              .map(a => ({
                label:     a.label,
                sentiment: r[a.key.toLowerCase().replace("_", "_")] || r[a.key] || 0,
              }))
              .filter(l => l.sentiment !== 0);

            return (
              <div key={r.id || i} className="bg-gray-50 rounded-xl p-3 mb-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-medium text-gray-700">{r.reviewer_name || "Ẩn danh"}</span>
                  <span className="text-xs text-gray-400">{r.review_date || ""}</span>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed mb-2">{r.text}</p>
                <div className="flex flex-wrap gap-1.5">
                  {labels.map((l, li) => (
                    <AspectChip key={li} label={l.label} sentiment={l.sentiment} />
                  ))}
                  {labels.length === 0 && (
                    <span className="text-xs text-gray-400">Không phát hiện khía cạnh</span>
                  )}
                </div>
              </div>
            );
          })}
          <p className="text-xs text-center text-gray-400 py-2">
            Hiển thị {reviews.length} comments
          </p>
        </>
      )}
    </div>
  );
}
