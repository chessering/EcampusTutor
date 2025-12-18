// components/SummaryComplete.jsx  (실제 컴포넌트 이름은 BlankComplete)
import React, { useState, useCallback } from "react";
import axios from "axios";
import "../styles/styles.css";
import { useNavigate, useLocation } from "react-router-dom";

export default function BlankComplete({ onBack }) {
  const navigate = useNavigate();
  const location = useLocation();
  const pdfUrl = location.state?.pdfUrl || null;

  const [isLoading, setIsLoading] = useState(false);

  const handleDownloadClick = useCallback(
    async (e) => {
      e.preventDefault();

      if (!pdfUrl) {
        alert("다운로드 링크 정보(pdfUrl)를 찾을 수 없습니다.");
        return;
      }

      const token = sessionStorage.getItem("accessToken");
      if (!token) {
        alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
        navigate("/login", { replace: true });
        return;
      }

      try {
        setIsLoading(true);

        // summary 쪽과 동일: base URL + pdfUrl로 바로 파일 요청
        const BASE_URL = "http://192.168.0.10:8000";
        const url = `${BASE_URL}${pdfUrl}`;

        const res = await axios.get(url, {
          responseType: "blob",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        // 파일명은 endpoint 마지막 조각 기준
        let filename = "blank-note.pdf";
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
      } catch (error) {
        console.error("빈칸 노트 다운로드 실패:", error);
        alert("파일 다운로드 중 오류가 발생했습니다.");
      } finally {
        setIsLoading(false);
      }
    },
    [pdfUrl, navigate]
  );

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
            빈칸 문제 노트 생성이 완료되었습니다!
          </p>

          <a
            href="#"
            onClick={handleDownloadClick}
            style={{
              display: "inline-block",
              marginTop: 24,
              textDecoration: "none",
              cursor: pdfUrl ? "pointer" : "not-allowed",
              fontSize: 22,
              fontWeight: 600,
              color: pdfUrl ? "#2563eb" : "#9ca3af", // 링크 느낌 + 비활성 시 회색
            }}
          >
            {isLoading
              ? "파일 다운로드 중..."
              : "→빈칸 문제 노트 다운로드←"}
          </a>
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
