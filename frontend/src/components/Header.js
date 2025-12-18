import React from "react";
import "../styles/Header.css";

export default function Header({ isAuthed, onLogoClick, onLoginClick, onLogoutClick }) {
  return (
    <header className="header">
      <div className="header__inner container">
        <button className="brand" onClick={onLogoClick} aria-label="홈으로">
          KHUNote
        </button>
        <nav className="nav">
          {isAuthed ? (
            <button className="nav__link" onClick={onLogoutClick}>
              로그아웃
            </button>
          ) : (
            <button className="nav__link" onClick={onLoginClick}>
              로그인
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
