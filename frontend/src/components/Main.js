import React from "react";
import { useNavigate } from 'react-router-dom'; 
import "../styles/main.css"

function Card({ title, onClick }) {
  return (
    <button className="card" onClick={onClick}>
      <span className="card__title">{title}</span>
    </button>
  );
}

export default function Main() {

  const navigate = useNavigate();

  return (
    <section className="container main">
      <div className="grid">
        <Card title="자료 생성하기" onClick={() => navigate("/data_select")} />
        <Card title="이전 기록 열람하기" onClick={() => navigate("/saved_quiz")} />
      </div>
    </section>
  );
}
