// src/components/SavedQuiz.js
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "../styles/styles.css";
import "../styles/mySection.css";

const COLOR_CLASSES = [
  "card--coral",
  "card--yellow",
  "card--mint",
  "card--blue",
  "card--purple",
  "card--apricot",
  "card--lemon",
  "card--tea",
  "card--powder",
  "card--lavender",
];

export default function SavedQuiz() {
  const navigate = useNavigate();

  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const fetchQuiz = async () => {
      const token = sessionStorage.getItem("accessToken");
      if (!token) {
        alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
        navigate("/login", { replace: true });
        return;
      }

      try {
        setLoading(true);
        setErrorMsg("");

        const res = await axios.get("http://192.168.0.10:8000/api/quiz", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        console.log("📥 /api/quiz 원본 응답:", res.data);

        // 최상위
        const root = res.data || {};
        const d1 = root.data; // { data: [...] } 또는 배열 또는 다른 형태

        let list = [];

        if (Array.isArray(d1)) {
          // case 1: { status, message, data: [ ... ] }
          list = d1;
        } else if (d1 && Array.isArray(d1.data)) {
          // ✅ 현재 케이스: { status, message, data: { data: [ ... ] } }
          list = d1.data;
        } else if (d1 && Array.isArray(d1.quizzes)) {
          list = d1.quizzes;
        } else {
          console.warn("⚠️ 예상치 못한 data 형식, 빈 배열로 처리:", d1);
        }

        console.log("📌 최종 quizzes 리스트:", list);
        setQuizzes(list);
      } catch (err) {
        console.error("저장된 퀴즈 목록 불러오기 실패:", err);
        setErrorMsg("저장된 문제 목록을 불러오는데 실패했습니다.");
        setQuizzes([]);
      } finally {
        setLoading(false);
      }
    };

    fetchQuiz();
  }, [navigate]);

  const isEmpty = !Array.isArray(quizzes) || quizzes.length === 0;

  return (
    <section className="page">
      <div className="container">

          <button
            type="button"
            onClick={() => navigate("/app")}
            className="btn btn--subtle"
            style={{
              height: 28,
              padding: "0 12px",
              background: "#f28a95",
              color: "#fff",
              boxShadow: "var(--shadow)",
              marginBottom: "20px",
              marginLeft: "80px",
            }}
          >
            &lt; 돌아가기
          </button>
        
        <div className="my-section-panel">
          <div className="my-section-header">
            <span className="my-section-title">My Section</span>
          </div>
          <div className="my-section-divider" />

          {loading && (
            <div
              style={{
                padding: 24,
                textAlign: "center",
                color: "#6b7280",
              }}
            >
              저장된 문제를 불러오는 중입니다...
            </div>
          )}

          {!loading && errorMsg && (
            <div
              style={{
                padding: 24,
                textAlign: "center",
                color: "#b91c1c",
              }}
            >
              {errorMsg}
            </div>
          )}

          {!loading && !errorMsg && (
            <div className="my-section-cards">
              {isEmpty ? (
                <div
                  style={{
                    padding: 24,
                    textAlign: "center",
                    color: "#6b7280",
                    width: "100%",
                  }}
                >
                  저장된 문제가 없습니다.
                </div>
              ) : (
                quizzes.map((item, idx) => {
                  const colorClass =
                    COLOR_CLASSES[idx % COLOR_CLASSES.length];

                  return (
                    <button
                      key={item.quizId}
                      type="button"
                      className={`my-section-card ${colorClass}`}
                      onClick={() =>
                        navigate(
                          `/saved_quiz/${encodeURIComponent(item.title)}`,
                          {
                            state: {
                              quizId: item.quizId,
                            },
                          }
                        )
                      }
                    >
                      {item.title}
                    </button>
                  );
                })
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
