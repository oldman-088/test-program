import { useState, type FormEvent } from "react";
import { DIFFICULTIES, formatDuration, toArabicDigits } from "../game/logic";
import type { GameResult } from "../game/types";
import { submitScore } from "../services/scoreApi";

type SubmitState = "idle" | "saving" | "saved" | "error";

interface EndScreenProps {
  result: GameResult;
  onPlayAgain: () => void;
  onChangeDifficulty: () => void;
  onScoreSaved: (id: number) => void;
}

export function EndScreen({
  result,
  onPlayAgain,
  onChangeDifficulty,
  onScoreSaved,
}: EndScreenProps) {
  const [name, setName] = useState("");
  const [state, setState] = useState<SubmitState>("idle");
  const [error, setError] = useState<string | null>(null);
  const config = DIFFICULTIES[result.difficulty];

  const trimmed = name.trim();
  const canSubmit = trimmed.length > 0 && trimmed.length <= 40 && state !== "saving";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    setState("saving");
    setError(null);
    try {
      const entry = await submitScore({
        player_name: trimmed,
        difficulty: result.difficulty,
        attempts: Math.max(1, result.attempts),
        duration_seconds: Math.max(1, result.durationSeconds),
        finished_at: new Date().toISOString(),
      });
      setState("saved");
      onScoreSaved(entry.id);
    } catch (caught) {
      console.error("Failed to submit score", caught);
      setState("error");
      setError("تعذّر حفظ النتيجة. تحقّق من الاتصال بالخادم وحاول مجددًا.");
    }
  }

  return (
    <div className="overlay" role="dialog" aria-modal="true" aria-labelledby="end-title">
      <div className="panel end-screen">
        <p className="end-screen__badge">🎉</p>
        <h2 id="end-title" className="end-screen__title">
          أكملت مستوى {config.label}!
        </h2>

        <ul className="end-screen__stats">
          <li>
            <span>المحاولات</span>
            <strong>{toArabicDigits(result.attempts)}</strong>
          </li>
          <li>
            <span>الأخطاء</span>
            <strong>{toArabicDigits(result.misses)}</strong>
          </li>
          <li>
            <span>الدقّة</span>
            <strong>{toArabicDigits(result.accuracy)}٪</strong>
          </li>
          <li>
            <span>الوقت</span>
            <strong dir="ltr">{formatDuration(result.durationSeconds)}</strong>
          </li>
          <li>
            <span>أفضل تتابع</span>
            <strong>{toArabicDigits(result.bestStreak)}</strong>
          </li>
        </ul>

        {state === "saved" ? (
          <p className="end-screen__saved" role="status">
            ✅ تم حفظ نتيجتك في لوحة الصدارة
          </p>
        ) : (
          <form className="end-screen__form" onSubmit={handleSubmit}>
            <label htmlFor="player-name">اسم اللاعب</label>
            <div className="end-screen__row">
              <input
                id="player-name"
                name="player-name"
                type="text"
                maxLength={40}
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="اكتب اسمك…"
                autoComplete="nickname"
                disabled={state === "saving"}
              />
              <button type="submit" className="button button--primary" disabled={!canSubmit}>
                {state === "saving" ? "جارٍ الحفظ…" : "احفظ النتيجة"}
              </button>
            </div>
            {error && (
              <p className="end-screen__error" role="alert">
                {error}
              </p>
            )}
            <p className="end-screen__note">النتيجة تُسجَّل على اسمك في لوحة الصدارة.</p>
          </form>
        )}

        <div className="end-screen__actions">
          <button type="button" className="button" onClick={onPlayAgain}>
            العب مرة أخرى
          </button>
          <button type="button" className="button button--ghost" onClick={onChangeDifficulty}>
            تغيير المستوى
          </button>
        </div>
      </div>
    </div>
  );
}
