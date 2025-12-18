// OptionSelect.jsx
import React, { useState } from "react";
import { useNavigate, useLocation } from 'react-router-dom';

export default function OptionSelect({ onBack, onNext }) {
  const [selected, setSelected] = useState(null); // "summary" | "blank" | "quiz" | null
  const [includeShort, setIncludeShort] = useState(false); // 단답형 포함 체크
  const pick = (type) => {
    setSelected(type);
    if (type !== "quiz") setIncludeShort(false);
  }
  
  const handleNext = () => {
    if (!selected) return;
    onNext?.({
        type: selected,
        from,
        files,
        ...(selected === "quiz" ? {includeShort} : {}),
    })

    navigate("/file_loading")
  }
  
  const isSel = (v) => selected === v;

  const navigate = useNavigate();
  const location = useLocation();
  const { from, files, url } = location.state || {};

  console.log("Option_select location.state: " , location.state)
  console.log("from:" , from)
  console.log("files: ", files);
  if (Array.isArray(files)) {
    console.log("file names: ", files.map(f => f.name));
  }

  return ( 
    <section className="main">
      <div
        className="container"
        style={{ paddingTop: 24, display: "flex", flexDirection: "column", alignItems: "center" }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: 640,
            marginBottom: 20,
            display: "flex",
            justifyContent: "flex-start",
          }}
        >
          <button
            type="button"
            onClick={onBack}
            className="btn btn--subtle"
            style={{
              height: 28,
              padding: "0 12px",
              background: "#f28a95",
              color: "#fff",
              border: 0,
              borderRadius: 999,
              boxShadow: "var(--shadow)",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            &lt; 돌아가기
          </button>
        </div>

        {/* 안내 박스 */}
        <div
          style={{
            width: "100%",
            maxWidth: 640,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 20,
          }}
        >
          <div
            style={{
              height: 54,
              borderRadius: 16,
              width: "100%",
              boxShadow: "var(--shadow)",
              background: "#fff",
              border: "1.5px solid #d7a7ff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#111",
              fontSize: 15,
            }}
          >
            원하는 옵션을 선택해 주세요
          </div>

          {/* 옵션 3개 */}
          <div
            style={{
              width: "100%",
              maxWidth: 720,
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 24,
            }}
          >
            <button
              type="button"
              onClick={() => pick("summary")}
              style={{
                height: 40,
                borderRadius: 12,
                border: "1px solid #e7d8ff",
                background: isSel("summary") ? "#d489ff" : "#f4eaff",
                color: "#111",
                cursor: "pointer",
                boxShadow: "var(--shadow)",
              }}
            >
              요약 노트
            </button>

            <button
              type="button"
              onClick={() => pick("blank")}
              style={{
                height: 40,
                borderRadius: 12,
                border: "1px solid #e7d8ff",
                background: isSel("blank") ? "#d489ff" : "#f4eaff",
                color: "#111",
                cursor: "pointer",
                boxShadow: "var(--shadow)",
                padding: "0 8px",
              }}
            >
              핵심 키워드
              <br />
              빈칸 채우기 노트
            </button>

            <button
              type="button"
              onClick={() => pick("quiz")}
              style={{
                height: 40,
                borderRadius: 12,
                border: "1px solid #e7d8ff",
                background: isSel("quiz") ? "#d489ff" : "#f4eaff",
                color: "#111",
                cursor: "pointer",
                boxShadow: "var(--shadow)",
              }}
            >
              예상문제 풀기
            </button>
          </div>

          {selected === "quiz" && (
            <div style={{ width: "100%", maxWidth: 640, display: "flex", alignItems: "center", justifyContent:"flex-end", gap: 10 }}>
                <span style={{ fontSize: 12, color: "#6b7280" }}>단답형 포함</span>
                <input
                    type="checkbox"
                    checked={includeShort}
                    onChange={(e) => setIncludeShort(e.target.checked)}
                    style={{ width: 16, height: 16, accentColor: "#f28a95" }}
                />
            </div>
          )}
          <div style={{ width: "100%", maxWidth: 640, display: "flex", justifyContent: "flex-end" }}>
            <button
              type="button"
              onClick={handleNext}
              disabled={!selected}
              style={{
                marginTop: 24,
                height: 34,
                padding: "0 16px",
                borderRadius: 999,
                border: 0,
                background: selected ? "#f28a95" : "#f2b7be",
                color: "#fff",
                cursor: selected ? "pointer" : "not-allowed",
                boxShadow: "var(--shadow)",
                fontSize: 13,
              }}
            >
              다음으로 &gt;
            </button>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 720px) {
          .opt-grid { grid-template-columns: 1fr !important; gap: 14px !important; }
        }
      `}</style>
    </section>
  );
}
