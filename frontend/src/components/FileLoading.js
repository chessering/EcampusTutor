import React from 'react';
import Lottie from 'react-lottie-player';
import animationData from "../asset/Davsan.json";
import "../styles/styles.css";
import "../styles/fileloading.css";

export default function FileLoading({progress = 0}) {

    const displayProgress = Math.round(progress);

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
          transform: "translateY(-100px)", 
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <div style={{ width: 300, height: 300 }}>
            <Lottie
              animationData={animationData}
              play={true}
              loop={true}
              style={{ width: "100%", height: "100%" }}
            />
          </div>

          <p style={{ 
            margin: 0, 
            color: 'black',
            fontFamily: "monospace", 
            fontSize: '30px',
            fontWeight: 'bold',
          }}>
            자료를 생성하는 중입니다. 잠시만 기다려 주세요..
          </p>
        </div>

        <div className="file-loading__progress">
          <div
            className="file-loading__progress-inner"
            style={{ width: `${displayProgress}%` }}
          />
        </div>

        <p className="file-loading__percent">
          {displayProgress}% 완료
        </p>

      </div>
    </div>
  );
}
