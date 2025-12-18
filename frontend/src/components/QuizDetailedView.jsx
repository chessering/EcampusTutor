// QuizDetailedView.jsx
import React from "react";
import "../styles/styles.css";
import "../styles/quiz.css";

/**
 * ✅ 혼합된 MULTIPLE 답안 포맷(0-base/1-base)이 섞여 있어도
 *    화면에서는 "사용자 답 체크" / "정답 표시"가 안정적으로 되도록 보정한 완성본.
 *
 * 전제:
 * - questions: /api/quiz/{quizId} 응답의 data.questions 배열 (correctAnswer, explanation 등 포함)
 * - answers:   { [questionNumber]: userAnswer } 형태 (SavedQuizDetail 또는 QuizDetailResult에서 넘어옴)
 *   - MULTIPLE: 숫자(0-base 또는 1-base가 섞여 있을 수 있음)
 *   - SHORT: 문자열
 */

export default function QuizDetailedView({ questions, answers, onBack }) {
  const getUserAnswerRaw = (qNum) => {
    // key가 숫자/문자열로 들어올 수 있어 둘 다 대응
    return answers?.[qNum] ?? answers?.[String(qNum)] ?? null;
  };

  // value를 "선택지 index(0-base)"로 바꿔보는 1차 변환
  const toIndexMaybe = (value, choicesLen) => {
    if (value === null || value === undefined || value === "") return null;
    const num = Number(value);
    if (!Number.isFinite(num)) return null;

    // 0-base 범위면 그대로 index
    if (num >= 0 && num <= choicesLen - 1) return num;

    // 1-base 범위면 index로 변환
    if (num >= 1 && num <= choicesLen) return num - 1;

    return null;
  };

  /**
   * correctAnswer/userAnswer가 섞여 있을 때(문제별로 0-base/1-base 혼재)
   * userAnswer가 어느 체계인지(0-base면 0~n-1, 1-base면 1~n)로 힌트를 얻어서
   * 둘 다 index(0-base)로 통일해 반환
   */
  const normalizePairToIndex = (correctAnswer, userAnswer, choicesLen) => {
    const cNum = Number(correctAnswer);
    const uNum = Number(userAnswer);

    const cIsNum = Number.isFinite(cNum);
    const uIsNum = Number.isFinite(uNum);

    // ✅ userAnswer가 0-base 범위라면 그 기준으로 맞춤
    if (uIsNum && uNum >= 0 && uNum <= choicesLen - 1) {
      const uIdx = uNum;

      if (cIsNum) {
        if (cNum >= 0 && cNum <= choicesLen - 1) return [cNum, uIdx]; // correct도 0-base
        if (cNum >= 1 && cNum <= choicesLen) return [cNum - 1, uIdx]; // correct는 1-base
      }
      return [toIndexMaybe(correctAnswer, choicesLen), uIdx];
    }

    // ✅ userAnswer가 1-base 범위라면 그 기준으로 맞춤
    if (uIsNum && uNum >= 1 && uNum <= choicesLen) {
      const uIdx = uNum - 1;

      if (cIsNum) {
        if (cNum >= 1 && cNum <= choicesLen) return [cNum - 1, uIdx]; // correct도 1-base
        if (cNum >= 0 && cNum <= choicesLen - 1) return [cNum, uIdx]; // correct는 0-base
      }
      return [toIndexMaybe(correctAnswer, choicesLen), uIdx];
    }

    // userAnswer가 없거나 판단 불가면 각각 독립적으로 변환
    return [toIndexMaybe(correctAnswer, choicesLen), toIndexMaybe(userAnswer, choicesLen)];
  };

  const computeIsCorrect = (q, userAnswerIdxOrText, correctIdxOrText) => {
    if (userAnswerIdxOrText == null || correctIdxOrText == null) return null;

    if (q.questionType === "MULTIPLE") {
      return Number(userAnswerIdxOrText) === Number(correctIdxOrText);
    }

    if (q.questionType === "SHORT") {
      return (
        String(userAnswerIdxOrText).trim().toLowerCase() ===
        String(correctIdxOrText).trim().toLowerCase()
      );
    }

    return null;
  };

  return (
    <section className="page">
      <div className="container quiz-container">
        <div className="quiz-sheet">
          <div className="quiz-list">
            {questions.map((q) => {
              const rawUser = getUserAnswerRaw(q.questionNumber);

              // ✅ API 응답 키 이름 (너가 준 /api/quiz/{id} 구조 기반)
              const rawCorrect = q.correctAnswer ?? null;
              const explanation =
                q.explanation || "해설이 아직 준비되지 않았습니다.";

              // MULTIPLE은 0/1-base 혼재 가능성 -> index(0-base)로 통일
              let userForCompare = rawUser;
              let correctForCompare = rawCorrect;

              if (q.questionType === "MULTIPLE") {
                const choicesLen = q.choices?.length ?? 0;
                const [correctIdx, userIdx] = normalizePairToIndex(
                  rawCorrect,
                  rawUser,
                  choicesLen
                );
                correctForCompare = correctIdx; // 0-base index
                userForCompare = userIdx;       // 0-base index
              }

              const isCorrect = computeIsCorrect(q, userForCompare, correctForCompare);

              return (
                <article key={q.questionNumber} className="quiz-question">
                  <div className="quiz-q-header">
                    <span className="quiz-q-label">문제 {q.questionNumber}</span>
                    <span
                      className="quiz-q-progress"
                      style={{
                        color:
                          isCorrect === true
                            ? "#2563eb"
                            : isCorrect === false
                            ? "#dc2626"
                            : "#6b7280",
                        fontWeight: 600,
                      }}
                    >
                      {isCorrect == null ? "" : isCorrect ? "정답" : "오답"}
                    </span>
                  </div>

                  <div className="quiz-q-body">
                    <p className="quiz-q-title">{q.questionText}</p>

                    {/* ✅ 객관식: 사용자 답 체크(읽기 전용) */}
                    {q.questionType === "MULTIPLE" && (
                      <ul className="quiz-q-choices quiz-q-choices--readonly">
                        {(q.choices ?? []).map((choice, idx) => {
                          const displayNum = idx + 1; // UI 표시는 1-based
                          return (
                            <li key={idx} className="quiz-q-choice">
                              <label>
                                <input
                                  type="radio"
                                  name={`q-${q.questionNumber}`}
                                  checked={Number(userForCompare) === idx} // ✅ 비교는 0-base index
                                  disabled
                                  readOnly
                                />
                                <span>
                                  {displayNum}. {choice}
                                </span>
                              </label>
                            </li>
                          );
                        })}
                      </ul>
                    )}

                    {/* ✅ 단답형: 내가 쓴 답 그대로 보여주기(읽기 전용) */}
                    {q.questionType === "SHORT" && (
                      <textarea
                        className="quiz-q-textarea"
                        value={rawUser ?? ""}
                        readOnly
                        disabled
                      />
                    )}

                    {/* ✅ 정답/해설 박스 */}
                    <div
                      style={{
                        marginTop: 12,
                        padding: "10px 12px",
                        borderRadius: 10,
                        fontSize: 12,
                        lineHeight: 1.6,
                        background:
                          isCorrect === true
                            ? "#E8F4FF"
                            : isCorrect === false
                            ? "#FFEAEA"
                            : "#fef9f9",
                        border: "1px solid",
                        borderColor:
                          isCorrect === true
                            ? "#3B82F6"
                            : isCorrect === false
                            ? "#EF4444"
                            : "#e5e7eb",
                        color:
                          isCorrect === true
                            ? "#1E3A8A"
                            : isCorrect === false
                            ? "#991B1B"
                            : "#4B5563",
                      }}
                    >
                      <div>
                        정답:{" "}
                        {q.questionType === "MULTIPLE" ? (
                          (() => {
                            // correctForCompare는 0-base index로 통일됨
                            const idx = Number(correctForCompare);
                            if (!Number.isFinite(idx)) return "정답 정보 없음";

                            const displayNum = idx + 1; // UI 표시용
                            const text = q.choices?.[idx] ?? "";
                            return text
                              ? `${displayNum}번 - ${text}`
                              : `${displayNum}번`;
                          })()
                        ) : (
                          String(rawCorrect ?? "")
                        )}
                      </div>

                      <div style={{ marginTop: 4 }}>해설: {explanation}</div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <div className="quiz-footer">
          <button
            type="button"
            className="btn btn--subtle quiz-submit-btn"
            onClick={onBack}
          >
            돌아가기 &gt;
          </button>
        </div>
      </div>
    </section>
  );
}
