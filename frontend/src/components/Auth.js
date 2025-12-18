import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from 'axios';
import "../styles/login.css";

export default function Auth() {
  const [id, setId] = useState("");
  const [pw, setPw] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!id || !pw) {
      alert("ecampus 아이디와 비밀번호를 입력해 주세요.");
      return;
    }

    setIsSubmitting(true);

    try {
      const res = await axios.post("http://192.168.0.10:8000/api/auth/signup", {
        id : id,
        password: pw,
      });

      if (res.data.status === 200) {
        alert("회원가입에 성공했습니다.");
        navigate("/login", { replace: true });
      } else {
        alert("실제 ecampus id 또는 비밀번호가 아닙니다");
      }
    } catch (error) {
        console.group("❌ 회원가입 요청 에러 상세");
        if (error.response) {
            console.log("📌 서버 응답 상태 코드:", error.response.status);
            console.log("📌 서버 응답 데이터:", error.response.data);
            console.log("📌 서버 응답 헤더:", error.response.headers);
          }
          // 2) 요청은 갔는데 응답이 아예 없는 경우
          else if (error.request) {
            console.log("📌 요청은 전송되었지만 응답이 없습니다:", error.request);
          }
          // 3) 기타 오류 (axios 내부 메시지 등)
          else {
            console.log("📌 오류 메시지:", error.message);
          }
        console.groupEnd();
      alert("실제 ecampus id 또는 비밀번호가 아닙니다");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="login">
      <div className="login__card">
        <h1 className="login__title">회원가입</h1>
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
          <div className="login__actions">
            <button
                onClick = {() => navigate(-1)}
                type="button" 
                className="btn btn--subtle"
            >
                돌아가기
            </button>
            <button type="submit" className="btn btn--primary" disabled={isSubmitting}>
              가입하기
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
