import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from 'react-router-dom';

export default function DataSelect({ onBack, onSubmitPdf, onSubmitUrl }) {
  const [mode, setMode] = useState(null); // null | 'pdf' | 'url'
  const [files, setFiles] = useState([]);
  const [url, setUrl] = useState("");
  const [limitNotice, setLimitNotice] = useState("");
  const fileInputRef = useRef(null);

  const navigate = useNavigate();

  const isPdf = mode === "pdf";
  const isUrl = mode === "url";

  const handlePickPdf = () => setMode("pdf");
  const handlePickVideo = () => setMode("url");

  useEffect(() => {
    return () => files.forEach((f) => URL.revokeObjectURL(f.url));
  }, [files]);

  const isDup = (arr, f) => arr.some((x) => x.file.name === f.name && x.file.size === f.size);

  const appendPdfFiles = (incomingList) => {
    const pdfs = incomingList.filter((f) => f.type === "application/pdf");
    if (pdfs.length === 0) return;

    setFiles((prev) => {
      const next = [...prev];
      const remain = Math.max(0, 5 - next.length);
      const candidates = pdfs.filter((f) => !isDup(next, f)).slice(0, remain);
      const withUrls = candidates.map((f) => ({ file: f, url: URL.createObjectURL(f) }));
      const updated = next.concat(withUrls);

      const skipped = pdfs.length - candidates.length;
      if (skipped > 0) {
        setLimitNotice(`일부 파일은 중복이거나 최대 개수(5개)를 초과하여 제외되었습니다.`);
        setTimeout(() => setLimitNotice(""), 2500);
      }
      return updated;
    });
  };

  const handleFilesChange = (e) => {
    const list = Array.from(e.target.files || []);
    appendPdfFiles(list);
    e.target.value = "";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const list = Array.from(e.dataTransfer.files || []);
    appendPdfFiles(list);
  };

  const handleDragOver = (e) => e.preventDefault();
  const pdfLabel = useMemo(() => "pdf 파일 선택", []);
  const removeOne = (idx) => {
    setFiles((prev) => {
      const next = [...prev];
      const [removed] = next.splice(idx, 1);
      if (removed) URL.revokeObjectURL(removed.url);
      return next;
    });
  };

  const remaining = Math.max(0, 5 - files.length);

  return (
    <section className="main">
      <div className="container" style={{ paddingTop: 24, display: "flex", flexDirection: "column", alignItems: "center" }}>
        {/* 돌아가기 버튼 */}
        <div style={{ width: "100%", maxWidth: 640, marginBottom: 20, display: "flex", justifyContent: "flex-start" }}>
          <button
            type="button"
            onClick={onBack}
            className="btn btn--subtle"
            style={{
              height: 28,
              padding: "0 12px",
              background: "#f28a95",
              color: "#fff",
              boxShadow: "var(--shadow)",
            }}
          >
            &lt; 돌아가기
          </button>
        </div>

        {/* 안내 인풋 */}
        <div style={{ width: "100%", maxWidth: 640, display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 20 }}>
          <div
            className="input"
            style={{
              backgroundColor: "#fff",
              border: "1px solid #df88ed",
              textAlign: "center",
              display: "flex",
              justifyContent: "center",
              placeItems: "center",
              height: 54,
              borderRadius: 16,
              width: "100%",
              boxShadow: "var(--shadow)",
              paddingLeft: 16,
            }}
          >제출하실 자료를 선택해 주세요</div>

          <div
            style={{
              width: "100%",
              display: "flex",
              justifyContent: "space-between",
              gap: 28,
            }}
          >
            <button
              type="button"
              onClick={handlePickPdf}
              className="btn btn--subtle"
              style={{
                flex: 1,
                height: 38,
                background: isPdf ? "#d489ff" : "#fdf8ff",
                color: isPdf ? "#000" : "#5c2430",
                border: "1px solid #e7d8ff",
                textAlign: "center",

                marginTop: 15,
              }}
            >
              강의자료 PDF
            </button>

            <button
              type="button"
              onClick={handlePickVideo}
              className="btn btn--subtle"
              style={{
                flex: 1,
                height: 38,
                background: isUrl ? "#d489ff" : "#f4eaff",
                color: isUrl ? "#000" : "#5c2430",
                border: "1px solid #e7d8ff",
                textAlign: "center",
                marginTop: 15,
              }}
            >
              강의 동영상 url
            </button>
          </div>

          <div style={{ width: "100%" }}>
            {isPdf && (
              <div style={{ marginTop: 16 }}>
                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  role="button"
                  tabIndex={0}
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={(e) => (e.key === "Enter" ? fileInputRef.current?.click() : null)}
                  style={{
                    background: "#fff",
                    border: "2px solid #DF88ED",
                    borderRadius: 14,
                    minHeight: 54,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: "var(--shadow)",
                    cursor: "pointer",
                    padding: "0 16px",
                  }}
                  data-testid="dropzone"
                  aria-label="PDF 파일을 선택하거나 끌어다 놓으세요"
                >
                  <span style={{ 
                    color: "#DF88ED", 
                    textAlign: "center", 
                    width: "100%",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    }}>
                        {pdfLabel}
                  </span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="application/pdf"
                    multiple
                    onChange={handleFilesChange}
                    hidden
                  />
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <small style={{ marginTop: 10, color: "#d7a7ff" }}>또는 pdf를 여기에 두기</small>
                  <small style={{ marginTop: 10, color: "#6b7280" }}>남은 슬롯: {remaining} / 5</small>
                </div>

                {limitNotice && <div style={{ marginTop: 8, color: "#b45309", fontSize: 13 }}>{limitNotice}</div>}

                {files.length > 0 && (
                  <div
                    style={{
                      marginTop: 16,
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                      gap: 14,
                    }}
                  >
                    {files.slice(0, 5).map((item, idx) => (
                      <div
                        key={item.url}
                        style={{
                          background: "#fff",
                          border: "1px solid #f199a2",
                          borderRadius: 12,
                          padding: 8,
                          boxShadow: "var(--shadow)",
                          position: "relative",
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => removeOne(idx)}
                          aria-label="Remove file"
                          style={{
                            position: "absolute",
                            top: 6,
                            right: 6,
                            border: 0,
                            background: "#f28a95",
                            color: "#fff",
                            borderRadius: 999,
                            width: 22,
                            height: 22,
                            cursor: "pointer",
                          }}
                        >
                          ×
                        </button>
                        <div style={{ height: 160, overflow: "hidden", borderRadius: 8, marginBottom: 8 }}>
                          <embed src={item.url} type="application/pdf" style={{ width: "100%", height: "100%", border: 0 }} />
                        </div>
                        <div style={{ fontSize: 12, color: "#333" }} title={item.file.name}>
                          {item.file.name}
                        </div>
                        <div style={{ fontSize: 11, color: "#6b7280" }}>
                          {(item.file.size / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {files.length > 0 && (
                  <div style={{ marginTop: 22, display: "flex", justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      className="btn btn--primary"
                      onClick={() => 
                        {
                          onSubmitPdf?.(files.map((f) => f.file));
                          navigate("/option_select", {
                            state: { from: "pdf", files: files.map((f) => f.file) },
                          });

                        }
                      }
                      style={{ background: "#f28a95" }}
                    >
                      다음으로 &gt;
                    </button>
                  </div>
                )}
              </div>
            )}

            {isUrl && (
              <div style={{ marginTop: 16, width: "100%" }}>
                <input
                  className="input"
                  placeholder="Ecampus URL 링크를 여기에 입력해 주세요.."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  style={{ backgroundColor: "#fff", height: 54, borderRadius: 16, width: "100%", boxShadow: "var(--shadow)", color: url ? "#111" : "#c9a8f5", textAlign: "center", paddingLeft: 16 }}
                />
                <div style={{ marginTop: 22, display: "flex", justifyContent: "flex-end" }}>
                  <button
                    type="button"
                    className="btn btn--primary"
                    onClick={() => 
                      {
                        onSubmitUrl?.(url)
                        navigate("/option_select", {
                          state: { from: "url", url },
                        });
                      }
                    }
                    disabled={!url}
                    style={{ background: "#f28a95" }}
                  >
                    다음으로 &gt;
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
