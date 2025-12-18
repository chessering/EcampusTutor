// components/QuizComplete.jsx
import React from "react";
import "../styles/styles.css";
import { useNavigate, useLocation } from "react-router-dom";

export default function QuizComplete() {

    const navigate = useNavigate();
    const location = useLocation();
    const result = location.state?.result || null;
    const quizId = result?.quizId ?? result?.quiz_id ?? null;

    const handleGoSolve = () => {
        if (!result) {
            alert("퀴즈 데이터가 없습니다. 다시 시도해 주세요.")
            navigate("/data_select")
            return;
        }
        navigate("/quiz_start", { state: { quizId } });
    }

    return (
        <div className="page">
            <div
                className="container"
                style={{
                minHeight: "calc(100vh - var(--header-h) - 80px)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                transform: "translateY(-90px)",
                gap: "16px", 
                }}
            >
                {/* 안내 문구 */}
                <p
                style={{
                    margin: 0,
                    fontSize: 28,
                    fontWeight: 600,
                    color: "#111827",
                    textAlign: "center",
                }}
                >
                예상 문제 생성이 완료되었습니다!
                </p>

                {/* 버튼 */}
                <button
                type="button"
                className="btn btn--subtle"
                onClick={handleGoSolve}
                style={{
                    marginTop: 24,
                    background: "#f28a95",
                    color: "#fff",
                    borderRadius: 14,
                    minWidth: 180,
                    height: 42,
                    fontSize: 14,
                    boxShadow: "var(--shadow)",
                }}
                >
                예상 문제 풀러가기 &gt;
                </button>
            </div>
        </div>
    );
}
