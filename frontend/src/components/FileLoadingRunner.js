// FileLoadingRunner.js
import React, { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import FileLoading from "./FileLoading";
import axios from "axios";

export default function FileLoadingRunner({ inputSource, option }) {
  const navigate = useNavigate();

  axios.defaults.baseURL = "http://192.168.0.10:8000";

  const [progress, setProgress] = useState(0);

  // quiz 전용
  const [taskId, setTaskId] = useState(null);
  const [quizReady, setQuizReady] = useState(false);
  const [quizStatusData, setQuizStatusData] = useState(null);
  const [initialQuizData, setInitialQuizData] = useState(null);

  const didRunRef = useRef(false);
  const pollTimerRef = useRef(null);

  const isQuiz = option?.type === "quiz";

  const getAuthHeader = useCallback(() => {
    const token = sessionStorage.getItem("accessToken");
    if (!token) return null;
    return { Authorization: `Bearer ${token}` };
  }, []);

  // ⬇ 진행률 타이머
  useEffect(() => {
    if (!inputSource || !option) return;

    const TOTAL_DURATION_MS = isQuiz ? 3 * 60 * 1000 : 10 * 60 * 1000;
    const start = performance.now();
    let frameId;

    const tick = (now) => {
      const elapsed = now - start;
      const ratio = Math.min(elapsed / TOTAL_DURATION_MS, 1);
      const percent = Math.round(ratio * 100);

      setProgress(percent);

      if (ratio < 1) frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);

    return () => {
      if (frameId) cancelAnimationFrame(frameId);
    };
  }, [inputSource, option, isQuiz]);

  useEffect(() => {
    if (!inputSource || !option) {
      navigate("/data_select", { replace: true });
      return;
    }
    if (didRunRef.current) return;
    didRunRef.current = true;

    const run = async () => {
      const { kind } = inputSource;
      const { type, includeShort } = option;

      let endpoint = "";
      let payload = null;
      let config = {};

      const authHeader = getAuthHeader();
      if (!authHeader) {
        alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
        navigate("/login", { replace: true });
        return;
      }

      if (kind === "pdf") {
        const formData = new FormData();
        inputSource.files.forEach((file) => formData.append("files", file));

        if (type === "summary") endpoint = "/api/notes/summary/files";
        else if (type === "blank") endpoint = "/api/notes/blank/files";
        else if (type === "quiz") {
          endpoint = "/api/quiz/generate/files";
          formData.append("includeShortAnswer", includeShort ? "true" : "false");
        }

        payload = formData;
        config = { headers: { ...authHeader } };
      } else if (kind === "url") {
        const { url } = inputSource;

        if (type === "summary") {
          endpoint = "/api/notes/summary/url";
          payload = { url };
        } else if (type === "blank") {
          endpoint = "/api/notes/blank/url";
          payload = { url };
        } else if (type === "quiz") {
          endpoint = "/api/quiz/generate/url";
          payload = { url, includeShortAnswer: includeShort };
        }

        config = {
          headers: { "Content-Type": "application/json", ...authHeader },
        };
      }

      if (!endpoint || !payload) {
        alert("잘못된 요청입니다. 다시 시도해 주세요.");
        navigate("/data_select", { replace: true });
        return;
      }

      try {
        const res = await axios.post(endpoint, payload, config);
        const data = res.data;
        const inner = data?.data || {};
        const pdfUrl = inner.pdfUrl || null;

        if (type === "summary") {
          setProgress(100);
          navigate("/summary_complete", { state: { pdfUrl } });
          return;
        }

        if (type === "blank") {
          setProgress(100);
          navigate("/blank_complete", { state: { pdfUrl } });
          return;
        }

        // ✅ quiz
        // 1) generate 응답은 저장해두고(선택)
        // 2) taskId 뽑아서 폴링 시작
        setInitialQuizData(inner);

        // 혹시 generate가 이미 COMPLETED면 즉시 ready 처리(폴링 불필요)
        if (inner?.status === "COMPLETED") {
          setQuizReady(true);
          return;
        }

        const tId = inner?.taskId;
        if (!tId) throw new Error("quiz generate 응답에 taskId가 없습니다.");
        setTaskId(tId);
      } catch (err) {
        console.group("❌ 자료 생성 실패");
        if (err.response) {
          console.log("상태 코드:", err.response.status);
          console.log("응답 데이터:", err.response.data);
        } else if (err.request) {
          console.log("요청은 갔지만 응답이 없음:", err.request);
        } else {
          console.log("Axios 설정 에러:", err.message);
        }
        console.groupEnd();

        alert("자료 생성 중 오류가 발생했습니다.");
        navigate("/data_select", { replace: true });
      }
    };

    run();
  }, [inputSource, option, navigate, getAuthHeader]);

  // ✅ quiz 폴링: 2분마다 task-status 호출 -> COMPLETED면 ready만 세팅 (generate 재호출 X)
  useEffect(() => {
    if (!isQuiz) return;
    if (!taskId) return;
    if (quizReady) return; // 이미 준비됐으면 폴링 중단

    const authHeader = getAuthHeader();
    if (!authHeader) {
      alert("로그인이 만료되었습니다. 다시 로그인해 주세요.");
      navigate("/login", { replace: true });
      return;
    }

    const stopPolling = () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };

    const checkStatusOnce = async () => {
      try {
        const res = await axios.get(`/api/quiz/task-status/${taskId}`, {
          headers: { ...authHeader },
        });

        console.log("[Quiz Polling] / task-status:", res.data);

        const statusData = res.data?.data || {};
        setQuizStatusData(statusData);

        if (statusData?.status === "COMPLETED") {
          stopPolling();
          setQuizReady(true);
        }
      } catch (err) {
        console.group("❌ 퀴즈 상태 폴링 실패");
        if (err.response) {
          console.log("상태 코드:", err.response.status);
          console.log("응답 데이터:", err.response.data);
        } else {
          console.log("에러:", err.message);
        }
        console.groupEnd();
      }
    };

    // ✅ 2분 주기
    pollTimerRef.current = setInterval(checkStatusOnce, 2 * 60 * 1000);

    return () => stopPolling();
  }, [isQuiz, taskId, quizReady, navigate, getAuthHeader]);

  // ✅ quiz 이동 조건:
  // - 3분 타이머(=progress 100) + quizReady(true) 이면 이동
  // - result는 task-status data 우선, 없으면 initialQuizData 넘김
  useEffect(() => {
    if (!isQuiz) return;

    if (progress === 100 && quizReady) {
      navigate("/quiz_complete", {
        state: {
          result: quizStatusData || initialQuizData,
          taskId,
        },
      });
    }
  }, [isQuiz, progress, quizReady, quizStatusData, initialQuizData, taskId, navigate]);

  return <FileLoading progress={progress} />;
}
