// src/components/QuizList.jsx
import React, { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import "../styles/styles.css";
import "../styles/quiz.css";

const CHUNK_SIZE = 3;

export default function QuizList() {
  const [loadedCount, setLoadedCount] = useState(CHUNK_SIZE);
  const [answers, setAnswers] = useState({});
  const [quizDetail, setQuizDetail] = useState(null);   // ✅ /api/quiz/{id} 응답 data 저장
  const [loading, setLoading] = useState(true);

  const listRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  // ✅ QuizStart에서 넘긴 quizId 받기
  const quizId = location.state?.quizId ?? null;

  // ✅ 상세 퀴즈 조회
  useEffect(() => {
    const fetchQuiz = async () => {
      if (!quizId) {
        alert("퀴즈 ID가 없습니다. 다시 시도해 주세요.");
        navigate("/data_select", { replace: true });
        return;
      }

      const token = sessionStorage.getItem("accessToken");
      if (!token) {
        alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
        navigate("/login", { replace: true });
        return;
      }

      try {
        setLoading(true);
        const res = await axios.get(
          `http://192.168.0.10:8000/api/quiz/${quizId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const raw = res.data ?? {};
        const inner = raw.data ?? null; // ✅ 너가 준 응답 기준: raw.data가 실제 payload
        setQuizDetail(inner);
      } catch (err) {
        console.group("퀴즈 상세 조회 실패");
        if (err.response) {
          console.log("상태 코드:", err.response.status);
          console.log("응답 데이터:", err.response.data);
        } else if (err.request) {
          console.log("요청은 갔지만 응답이 없음:", err.request);
        } else {
          console.log("Axios 설정 에러:", err.message);
        }
        console.groupEnd();

        alert("퀴즈 정보를 불러오지 못했습니다.");
        navigate("/data_select", { replace: true });
      } finally {
        setLoading(false);
      }
    };

    fetchQuiz();
  }, [quizId, navigate]);

  // ✅ 이제 questions는 quizDetail에서 가져온다
  const questions = quizDetail?.questions ?? [];
  const visibleQuestions = questions.slice(0, loadedCount);

  const handleLoadMore = useCallback(() => {
    setLoadedCount((prev) => {
      const next = prev + CHUNK_SIZE;
      return next > questions.length ? questions.length : next;
    });
  }, [questions.length]);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;

    const onScroll = () => {
      const { scrollTop, clientHeight, scrollHeight } = el;
      if (scrollTop + clientHeight >= scrollHeight - 80) {
        if (loadedCount < questions.length) handleLoadMore();
      }
    };

    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, [handleLoadMore, loadedCount, questions.length]);

  // 객관식: 1~4 저장
  const handleChoiceChange = (questionNumber, choiceIdx) => {
    setAnswers((prev) => ({ ...prev, [questionNumber]: choiceIdx + 1 }));
  };

  // 단답형: 문자열 저장
  const handleShortChange = (questionNumber, text) => {
    setAnswers((prev) => ({ ...prev, [questionNumber]: text }));
  };

  const handleSubmit = async () => {
    const token = sessionStorage.getItem("accessToken");
    if (!token) {
      alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
      navigate("/login", { replace: true });
      return;
    }

    try {
      const answerItems = questions
        .map((q) => {
          const rawValue = answers[q.questionNumber];
          if (rawValue === undefined || rawValue === null) return null;

          let strValue;
          if (typeof rawValue === "number") strValue = String(rawValue);
          else strValue = String(rawValue).trim();

          if (!strValue) return null;

          return {
            questionNumber: q.questionNumber,
            questionType: q.questionType, // ✅ 새 API도 동일 키 사용
            answer: strValue,
          };
        })
        .filter(Boolean);

      if (answerItems.length === 0) {
        alert("최소 한 문제 이상 답을 입력해 주세요.");
        return;
      }

      const answerPayload = {
        quizId: quizId ?? 0, // ✅ quizId는 이제 확실히 있음
        answers: answerItems,
      };

      const res = await axios.post(
        "http://192.168.0.10:8000/api/quiz/submit",
        answerPayload,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      const raw = res.data ?? {};
      const inner = raw.data ?? raw;

      const gradedQuestions = inner.questions || raw.questions || [];

      let correctCount = 0;
      gradedQuestions.forEach((gq) => {
        const userAnswer = answers[gq.questionNumber];
        const userNorm = String(userAnswer ?? "").trim().toLowerCase();
        const correctNorm = String(gq.correctAnswer ?? "").trim().toLowerCase();

        if (gq.questionType === "MULTIPLE") {
          if (userNorm && userNorm === correctNorm) correctCount++;
        } else if (gq.questionType === "SHORT") {
          if (userNorm && userNorm === correctNorm) correctCount++;
        }
      });

      const totalQuestions =
        typeof inner.totalQuestions === "number"
          ? inner.totalQuestions
          : questions.length;

      const serverAnswers = gradedQuestions;

      navigate("/quiz_result", {
        state: {
          quizId,
          answers,
          correctCount,
          totalQuestions,
          serverAnswers,
        },
      });
    } catch (err) {
      console.group("퀴즈 채점(제출) 실패");
      if (err.response) {
        console.log("상태 코드: ", err.response.status);
        console.log("응답 데이터: ", err.response.data);
      } else if (err.request) {
        console.log("요청은 갔지만 응답이 없음: ", err.request);
      } else {
        console.log("Axios 설정 에러: ", err.message);
      }
      console.groupEnd();

      alert("퀴즈 제출 중 오류가 발생했습니다.");
    }
  };

  if (loading) {
    return (
      <section className="page">
        <div className="container quiz-container">
          <div className="quiz-sheet">
            <div className="quiz-list" style={{ padding: 24 }}>
              불러오는 중...
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (!quizDetail || questions.length === 0) {
    return (
      <section className="page">
        <div className="container quiz-container">
          <div className="quiz-sheet">
            <div className="quiz-list" style={{ padding: 24 }}>
              퀴즈 문항이 없습니다.
            </div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <div className="container quiz-container">
        <div className="quiz-sheet">
          <div ref={listRef} className="quiz-list">
            {visibleQuestions.map((q) => (
              <article key={q.questionNumber} className="quiz-question">
                <div className="quiz-q-header">
                  <span className="quiz-q-label">문제 {q.questionNumber}</span>
                </div>

                <div className="quiz-q-body">
                  <p className="quiz-q-title">{q.questionText}</p>

                  {q.questionType === "MULTIPLE" && (
                    <ul className="quiz-q-choices">
                      {(q.choices ?? []).map((choice, cIdx) => (
                        <li key={cIdx} className="quiz-q-choice">
                          <label>
                            <input
                              type="radio"
                              name={`q-${q.questionNumber}`}
                              checked={answers[q.questionNumber] === cIdx + 1}
                              onChange={() =>
                                handleChoiceChange(q.questionNumber, cIdx)
                              }
                            />
                            <span>{choice}</span>
                          </label>
                        </li>
                      ))}
                    </ul>
                  )}

                  {q.questionType === "SHORT" && (
                    <textarea
                      className="quiz-q-textarea"
                      placeholder="답안을 입력해 주세요."
                      value={answers[q.questionNumber] || ""}
                      onChange={(e) =>
                        handleShortChange(q.questionNumber, e.target.value)
                      }
                    />
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="quiz-footer">
          <button
            type="button"
            className="btn btn--subtle quiz-submit-btn"
            onClick={handleSubmit}
          >
            제출하기 &gt;
          </button>
        </div>
      </div>
    </section>
  );
}
