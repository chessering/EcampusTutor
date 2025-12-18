// QuizDetailResult.js
import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import QuizDetailedView from "./QuizDetailedView";

export default function QuizDetailResult() {
  const navigate = useNavigate();
  const location = useLocation();

  // QuizResult 에서 넘겨준 값들 (최신 흐름)
  const { quizId, answers } = location.state || {};

  const [loading, setLoading] = useState(true);
  const [questions, setQuestions] = useState([]);

  useEffect(() => {
    // 필수 값 없으면 되돌리기
    if (!quizId || !answers) {
      alert("퀴즈 정보를 찾을 수 없습니다.");
      navigate("/data_select", { replace: true });
      return;
    }

    const token = sessionStorage.getItem("accessToken");
    if (!token) {
      alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
      navigate("/login", { replace: true });
      return;
    }

    const fetchDetail = async () => {
      try {
        setLoading(true);
        const res = await axios.get(
          `http://192.168.0.10:8000/api/quiz/${quizId}`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        // 너가 준 응답 구조: { status, message, data: { questions: [...] } }
        const data = res.data?.data || {};
        const qs = data.questions || [];

        setQuestions(qs);
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

        alert("퀴즈 상세 정보를 불러오지 못했습니다.");
        navigate("/quiz_result", { replace: true });
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [quizId, answers, navigate]);

  if (loading) return null;
  if (!questions.length) {
    alert("퀴즈 문항이 없습니다.");
    navigate("/quiz_result", { replace: true });
    return null;
  }

  return (
    <QuizDetailedView
      questions={questions} // ✅ /api/quiz/{id}에서 받은 문항(정답/해설 포함)
      answers={answers}     // ✅ 사용자가 입력한 답(그대로 표시)
      onBack={() => navigate(-1)}
    />
  );
}
