// QuizResult.js
import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import "../styles/styles.css";
import "../styles/quiz.css";

export default function QuizResult() {
  const navigate = useNavigate();
  const location = useLocation();

  const [showSaveModal, setShowSaveModal] = useState(false);
  const [title, setTitle] = useState("");
  const [showSaveNotice, setShowSaveNotice] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // ✅ QuizList에서 넘어오는 최신 흐름: quizId는 최상위로 온다
  const {
    quizId,
    answers,
    correctCount,
    totalQuestions,
    serverAnswers,
  } = location.state || {};

  const handleSaveClick = () => setShowSaveModal(true);

  const handleSaveConfirm = async () => {
    if (!title.trim()) return;

    if (!quizId) {
      alert("퀴즈 ID 정보를 찾을 수 없습니다. 다시 시도해 주세요.");
      return;
    }

    const token = sessionStorage.getItem("accessToken");
    if (!token) {
      alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
      navigate("/login", { replace: true });
      return;
    }

    try {
      setIsSaving(true);

      const payload = {
        quizId: quizId,      // number
        title: title.trim(), // string
      };

      const res = await axios.post(
        "http://192.168.0.10:8000/api/quiz/save",
        payload,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      console.log("퀴즈 저장 응답:", res.data);

      setShowSaveModal(false);
      setShowSaveNotice(true);
    } catch (error) {
      console.error("퀴즈 저장 실패:", error);
      alert("퀴즈 저장 중 오류가 발생했습니다.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveCancel = () => {
    if (isSaving) return;
    setShowSaveModal(false);
  };

  const handleGoDetail = () => {
    if (!quizId) {
      alert("퀴즈 ID 정보를 찾을 수 없습니다. 다시 시도해 주세요.");
      navigate("/data_select");
      return;
    }
    if (!answers) {
      alert("사용자 답안 정보가 없습니다. 다시 시도해 주세요.");
      navigate("/data_select");
      return;
    }

    // ✅ 해설 보기: quizId + answers(내가 입력한 답) 전달
    navigate("/quiz_detail_result", {
      state: {
        quizId,
        answers,
      },
    });
  };

  return (
    <div className="page">
      <div
        className="container"
        style={{
          minHeight: `calc(100vh - var(--header-h) - 80px)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: 960,
            background: "#ffffff",
            borderRadius: "var(--radius)",
            boxShadow: "var(--shadow)",
            padding: "80px 40px",
            textAlign: "center",
            transform: "translateY(-90px)",
          }}
        >
          <div
            style={{
              fontSize: 20,
              lineHeight: 1.7,
              color: "#111827",
              marginBottom: 48,
            }}
          >
            <div>수고하셨습니다.</div>
            <div>맞은 문제의 갯수는</div>
            <div style={{ marginTop: 12, fontWeight: 600 }}>
              {correctCount} / {totalQuestions} 입니다.
            </div>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 40,
            }}
          >
            <button
              type="button"
              onClick={() => navigate("/app")}
              style={{
                minWidth: 120,
                height: 36,
                borderRadius: 999,
                border: "none",
                background: "#f28a95",
                color: "#ffffff",
                fontSize: 14,
                cursor: "pointer",
                boxShadow: "var(--shadow)",
              }}
            >
              돌아가기 &gt;
            </button>

            <button
              type="button"
              onClick={handleSaveClick}
              style={{
                minWidth: 120,
                height: 36,
                borderRadius: 999,
                border: "none",
                background: "#f28a95",
                color: "#ffffff",
                fontSize: 14,
                cursor: "pointer",
                boxShadow: "var(--shadow)",
              }}
            >
              기록 저장하기 &gt;
            </button>

            <button
              type="button"
              onClick={handleGoDetail}
              style={{
                minWidth: 120,
                height: 36,
                borderRadius: 999,
                border: "none",
                background: "#f28a95",
                color: "#ffffff",
                fontSize: 14,
                cursor: "pointer",
                boxShadow: "var(--shadow)",
              }}
            >
              해설 보기 &gt;
            </button>
          </div>
        </div>
      </div>

      {showSaveModal && (
        <div className="quiz-save-overlay">
          <div className="quiz-save-dialog">
            <p className="quiz-save-title">제목을 입력해 주세요</p>
            <input
              className="quiz-save-input"
              placeholder="여기에 입력"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isSaving}
            />

            <button
              type="button"
              className="quiz-save-button"
              onClick={handleSaveConfirm}
              disabled={!title.trim() || isSaving}
            >
              {isSaving ? "저장 중..." : "저장하기"}
            </button>

            <button
              type="button"
              className="quiz-save-close"
              onClick={handleSaveCancel}
              disabled={isSaving}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {showSaveNotice && (
        <div className="quiz-save-overlay">
          <div className="quiz-save-dialog">
            <p className="quiz-save-title">저장이 완료되었습니다!</p>

            <p className="quiz-save-desc">
              저장된 문제는 &quot;이전 기록 불러오기&quot;에서 확인 가능합니다.
            </p>

            <button
              type="button"
              className="quiz-save-button"
              onClick={() => {
                setShowSaveNotice(false);
                navigate("/app");
              }}
            >
              돌아가기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
