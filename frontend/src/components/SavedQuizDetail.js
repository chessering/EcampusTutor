import React, { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import axios from "axios";
import QuizDetailedView from "./QuizDetailedView";

export default function SavedQuizDetail() {
  const navigate = useNavigate();
  const location = useLocation();

  const [questions, setQuestions] = useState(null);
  const [answers, setAnswers] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  const quizId = location.state?.quizId;

  useEffect(() => {
    if (!quizId && quizId !== 0) {
      setErrorMsg("퀴즈 ID 정보를 찾을 수 없습니다.");
      setLoading(false);
      return;
    }

    const fetchQuizDetail = async () => {
      const token = sessionStorage.getItem("accessToken");
      if (!token) {
        alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
        navigate("/login", { replace: true });
        return;
      }

      try {
        setLoading(true);
        setErrorMsg("");

        const res = await axios.get(
          `http://192.168.0.10:8000/api/quiz/${quizId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const data = res.data?.data;
        if (!data) {
          setErrorMsg("퀴즈 데이터를 찾을 수 없습니다.");
          setLoading(false);
          return;
        }

        const questionList = data.questions || [];

        setQuestions(questionList);

        const initialAnswers = {};
          questionList.forEach((q) => {
            if (q.userAnswer === null || q.userAnswer === undefined) {
              initialAnswers[q.questionNumber] = null;
            } else {
              if (q.questionType === "MULTIPLE") {
                initialAnswers[q.questionNumber] = Number(q.userAnswer);
              } else {
                initialAnswers[q.questionNumber] = String(q.userAnswer);
              }
            }
        });

        setAnswers(initialAnswers);
      } catch (err) {
        console.error("저장된 퀴즈 상세 불러오기 실패:", err);
        setErrorMsg("퀴즈 상세 정보를 불러오는 데 실패했습니다.");
      } finally {
        setLoading(false);
      }
    };

    fetchQuizDetail();
  }, [quizId, navigate]);

  if (loading) {
    return (
      <section className="page">
        <div className="container">
          <p>저장된 퀴즈를 불러오는 중입니다...</p>
        </div>
      </section>
    );
  }

  if (errorMsg) {
    return (
      <section className="page">
        <div className="container">
          <p style={{ color: "#b91c1c" }}>{errorMsg}</p>
          <button
            type="button"
            onClick={() => navigate("/saved_quiz")}
            style={{
              marginTop: 16,
              padding: "8px 16px",
              borderRadius: 999,
              border: "none",
              background: "#f28a95",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            목록으로 돌아가기
          </button>
        </div>
      </section>
    );
  }

  if (!questions || !answers) {
    return (
      <section className="page">
        <div className="container">
          <p>퀴즈 데이터를 불러오지 못했습니다.</p>
        </div>
      </section>
    );
  }

  return (
    <QuizDetailedView
      questions={questions}
      answers={answers}
      serverAnswers={questions}
      onBack={() => navigate("/saved_quiz")}
    />
  );
}
