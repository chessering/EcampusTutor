import React from "react";
import "../styles/styles.css";
import "../styles/intro.css";
import imgfile from "../asset/khunote_background.png"

export default function Intro() {
  return (
    <section className="hero">
      <div className="container intro__wrap">
        <div
          className="intro__card"
          style={{ backgroundImage: `url(${imgfile})` }} /* public/hero.jpg 배치 추천 */
        >
          <div className="intro__overlay" />
          <div className="intro__content">
            <h1 className="intro__title">KHUNote</h1>
            <p className="intro__subtitle" style={{whiteSpace: "pre-wrap"}}>
              {`강의에서 시험까지, \nKHUNote가 당신의 공부를 더 쉽게 만들어 드립니다.`}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
