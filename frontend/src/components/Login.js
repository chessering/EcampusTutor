import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "../styles/login.css";

export default function Login({ onSubmit }) {
  const [id, setId] = useState("");
  const [pw, setPw] = useState("");
  const [errorMsg, setErrorMsg] = useState("");    // ⬅ 로그인 에러 메시지
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setErrorMsg(""); // 이전 에러 초기화

    if (!id || !pw) {
      setErrorMsg("id와 비밀번호를 모두 입력해 주세요.");
      return;
    }

    try {
      setIsSubmitting(true);

      // 🔗 실제 로그인 엔드포인트
      const res = await axios.post("http://192.168.0.10:8000/api/auth/login", {
        id: id,
        password: pw,
      });

      console.log("📌 로그인 응답:", res.data);

      if (res.data.status === 200) {
        const { access_token, refresh_token, user_id } = res.data.data || {};

        // 필요하면 토큰 저장 (예: 세션 스토리지)
        if (access_token) {
          sessionStorage.setItem("accessToken", access_token);
        }
        if (refresh_token) {
          sessionStorage.setItem("refreshToken", refresh_token);
        }
        if (user_id) {
          sessionStorage.setItem("userId", String(user_id));
        }
        sessionStorage.setItem("userLoginId", id);

        // 상위(AppShell)에서 isAuthed 처리 + 라우팅
        onSubmit();
      } else {
        setErrorMsg("id 또는 비밀번호가 틀립니다.");
      }
    } catch (error) {
      console.group("❌ 로그인 에러");
      if (error.response) {
        console.log("상태 코드:", error.response.status);
        console.log("응답 데이터:", error.response.data);
      } else if (error.request) {
        console.log("요청만 보내고 응답 없음:", error.request);
      } else {
        console.log("에러 메시지:", error.message);
      }
      console.groupEnd();

      setErrorMsg("id 또는 비밀번호가 틀립니다.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="login">
      <div className="login__card">
        <h1 className="login__title">KHUNote</h1>
        <form className="login__form" onSubmit={handleSubmit}>
          <input
            className="input"
            placeholder="ecampus 아이디"
            value={id}
            onChange={(e) => setId(e.target.value)}
          />
          <input
            className="input"
            type="password"
            placeholder="ecampus 비밀번호"
            value={pw}
            onChange={(e) => setPw(e.target.value)}
          />

          {/* ⬇ 비밀번호 아래에만 에러 문구 노출 (처음에는 안 보임) */}
          {errorMsg && (
            <p
              style={{
                margin: "4px 0 0 4px",
                fontSize: "12px",
                color: "#dc2626", // 빨간색
              }}
            >
              {errorMsg}
            </p>
          )}

          <div className="login__actions">
            <button
              onClick={() => navigate("/auth")}
              type="button"
              className="btn btn--subtle"
            >
              회원가입
            </button>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? "로그인 중..." : "로그인"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
