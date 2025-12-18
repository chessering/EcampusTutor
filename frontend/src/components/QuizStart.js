// components/QuizStart.jsx
import React from "react";
import "../styles/styles.css";
import { useNavigate, useLocation } from "react-router-dom";

export default function QuizStart() {

    const navigate = useNavigate();
    const location = useLocation();

    const quizId = location.state?.quizId ?? null;

    const handleStart = () => {
        if (!quizId) {
            alert("퀴즈 데이터가 없습니다. 다시 시도해 주세요.")
            navigate("/data_select")
            return;
        }
        navigate("/quiz_list", { state: { quizId } });
    }

    return (
        <div className="page">
            <div
                className="container"
                style={{
                minHeight: "calc(100vh - var(--header-h) - 80px)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                transform: "translateY(-90px)"
                }}
            >
                <div
                style={{
                    background: "#ffffff",
                    width: "100%",
                    maxWidth: 900,
                    borderRadius: 20,
                    boxShadow: "var(--shadow)",
                    padding: "80px 20px",
                    textAlign: "center",
                }}
                >
                <p
                    style={{
                    margin: 0,
                    fontSize: 22,
                    color: "#111827",
                    }}
                >
                    행운을 빕니다.
                </p>

                <p
                    style={{
                    marginTop: 10,
                    fontSize: 20,
                    color: "#111",
                    fontWeight: 500,
                    }}
                >
                    Good Luck!
                </p>

                <button
                    type="button"
                    className="btn btn--subtle"
                    onClick={handleStart}
                    style={{
                    marginTop: 40,
                    width: "60%",
                    height: 46,
                    background: "#f28a95",
                    color: "#fff",
                    borderRadius: 14,
                    fontSize: 15,
                    boxShadow: "var(--shadow)",
                    }}
                >
                    시작하기
                </button>
                </div>
            </div>
        </div>
    );
}
