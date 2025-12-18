import React, { useEffect, useMemo, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import Header from "./components/Header";
import Intro from "./components/Intro";
import Login from "./components/Login";
import Auth from "./components/Auth";
import Main from "./components/Main";
import SavedQuiz from "./components/SavedQuiz";
import SavedQuizDetail from "./components/SavedQuizDetail";
import DataSelect from "./components/DataSelect";
import OptionSelect from "./components/OptionSelect";
import FileLoading from "./components/FileLoading";
import FileLoadingRunner from "./components/FileLoadingRunner";
import SummaryComplete from "./components/SummaryCompleted";
import BlankComplete from "./components/BlankCompleted";
import QuizComplete from "./components/QuizCompleted";
import QuizStart from "./components/QuizStart";
import QuizList from "./components/QuizList";
import QuizResult from "./components/QuizResult";
import QuizDetailResult from "./components/QuizDetailResult";

import "./styles/styles.css";

function AppShell() {
  const [isAuthed, setIsAuthed] = useState(() => {
    return sessionStorage.getItem("authed") === "true";
  });

  const [inputSource, setInputSource] = useState(null);
  const [option, setOption] = useState(null);

  const location = useLocation();
  const navigate = useNavigate();

  // 로그인 화면만 색상 반전
  const themeClass = useMemo(
    () => (location.pathname === "/login"  || location.pathname === "/auth" ? "theme-inverted" : "theme-default"),
    [location.pathname]
  );

  function handleLogin() {
    setIsAuthed(true);
    sessionStorage.setItem("authed", "true");
    navigate("/app", { replace: true });
  }

  function handleLogout() {
    // 상태 초기화 + 세션 초기화 + 라우팅
    setIsAuthed(false);
    sessionStorage.removeItem("authed");
    navigate("/", { replace: true });
  }

  function handleSubmitPdf(files) {
    // files: File[] (DataSelect에서 넘겨줌)
    setInputSource({ kind: "pdf", files });
    navigate("/option_select");
  }

  function handleSubmitUrl(url) {
    setInputSource({ kind: "url", url });
    navigate("/option_select");
  }

  function handleOptionNext({ type, includeShort }) {

    setOption({ type, includeShort: !!includeShort });

    navigate("/file_loading");
  }

  return (
    <div className={`app-shell ${themeClass}`}>
      <Header
        isAuthed={isAuthed}
        onLogoClick={() => navigate("/app")}
        onLoginClick={() => navigate("/login")}
        onLogoutClick={handleLogout}
      />
      <main className="page">
        <Routes>
          <Route path="/" element={<Intro />} />
          <Route
            path="/login"
            element={<Login onSubmit={handleLogin} />}
          />
          <Route
            path="/auth"
            element={<Auth/>}
          />
          <Route
            path="/app"
            element={isAuthed ? <Main /> : <Navigate to="/" replace />}
          />
          <Route path="/main" element={<Main/>}/>

          <Route path="/saved_quiz">
            <Route index element={<SavedQuiz/>}/>
            <Route path=":quizName" element={<SavedQuizDetail/>}/>
          </Route>

          <Route 
            path="/data_select" 
            element={<DataSelect
               onBack={() => navigate("/main")}
               onSubmitPdf={handleSubmitPdf}
               onSubmitUrl={handleSubmitUrl}
               />
            }
          />
          <Route 
            path="/option_select" 
            element={<OptionSelect 
              onBack={() => navigate(-1)}
              onNext={handleOptionNext}
              />
            }
          />
          <Route 
            path="/file_loading" 
            element={
              <FileLoadingRunner
                inputSource={inputSource}
                option={option}
              />
            }
          />
          <Route 
            path="/summary_complete" 
            element={<SummaryComplete onBack={() => navigate("/app")}/>}
          />
          <Route 
            path="/blank_complete" 
            element={<BlankComplete onBack={() => navigate("/app")}/>}
          />
          <Route 
            path="/quiz_complete" 
            element={<QuizComplete/>}
          />
          <Route 
            path="/quiz_start" 
            element={<QuizStart/>}
          />
          <Route 
            path="/quiz_list" 
            element={<QuizList/>}
          />
          <Route path="/quiz_result" element={<QuizResult/>}/>
          <Route path="/quiz_detail_result" element={<QuizDetailResult/>}/>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
