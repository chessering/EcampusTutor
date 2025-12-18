// SummaryCompleted.js
import React from "react";
import "../styles/styles.css";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";

export default function SummaryComplete({ onBack }) {
  const navigate = useNavigate();
  const location = useLocation();
  const pdfUrl = location.state?.pdfUrl || null;

  const handleDownload = async () => {
    if (!pdfUrl) {
      alert("다운로드 링크가 없습니다. 다시 시도해 주세요.");
      return;
    }

    const token = sessionStorage.getItem("accessToken");
    if (!token) {
      alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
      navigate("/login", { replace: true });
      return;
    }

    try {
      const BASE_URL = "http://192.168.0.10:8000";

      // 👉 서버에서 준 pdfUrl 그대로 Base URL 뒤에 붙이기
      const url = `${BASE_URL}${pdfUrl}`;

      const res = await axios.get(url, {
        responseType: "blob",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // 파일 이름은 일단 endpoint 마지막 부분 기준
      let filename = "summary.pdf";
      const parts = pdfUrl.split("/");
      if (parts.length > 0) {
        filename = parts[parts.length - 1] || filename;
      }

      // Blob → 다운로드 트리거
      const blobUrl = window.URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error("📄 파일 다운로드 실패:", err);
      alert("파일 다운로드 중 오류가 발생했습니다.");
    }
  };

  return (
    <div className="page">
      <div
        className="container"
        style={{
          minHeight: "calc(100vh - var(--header-h) - 80px)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "flex-start",
          paddingTop: 80,
        }}
      >
        {/* 가운데 카드 */}
        <div
          style={{
            width: "100%",
            maxWidth: 720,
            background: "#ffffff",
            borderRadius: 18,
            border: "2px solid #f28a95",
            boxShadow: "var(--shadow)",
            padding: "32px 40px",
            textAlign: "center",
          }}
        >
          <p
            style={{
              margin: 0,
              fontSize: 20,
              fontWeight: 500,
              color: "#111827",
            }}
          >
            요약 노트 생성이 완료되었습니다!
          </p>

          <button
            type="button"
            style={{
              marginTop: 24,
              border: "none",
              background: "transparent",
              cursor: pdfUrl ? "pointer" : "not-allowed",
              fontSize: 22,
              fontWeight: 600,
              color: pdfUrl ? "#2563eb" : "#9ca3af",
            }}
            onClick={handleDownload}
            disabled={!pdfUrl}
          >
            →요약 노트 다운로드←
          </button>
        </div>

        <div
          style={{
            marginTop: 40,
            width: "100%",
            maxWidth: 720,
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <button
            type="button"
            className="btn btn--subtle"
            onClick={onBack}
            style={{
              background: "#f28a95",
              color: "#fff",
              minWidth: 130,
              height: 44,
              fontSize: 14,
              borderRadius: 14,
              boxShadow: "var(--shadow)",
            }}
          >
            &lt; 돌아가기
          </button>

          <button
            type="button"
            className="btn btn--subtle"
            onClick={() => navigate("/option_select")}
            style={{
              background: "#f28a95",
              color: "#fff",
              minWidth: 150,
              height: 44,
              fontSize: 14,
              borderRadius: 14,
              boxShadow: "var(--shadow)",
              whiteSpace: "pre-line",
            }}
          >
            예상 문제까지
            <br />
            출제하기
          </button>
        </div>
      </div>
    </div>
  );
}
