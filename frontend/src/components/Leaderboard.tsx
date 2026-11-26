import { useEffect, useState } from "react";
import { DIFFICULTIES, formatDuration, toArabicDigits } from "../game/logic";
import type { Difficulty } from "../game/types";
import { fetchLeaderboard, type Leaderboard as LeaderboardData } from "../services/scoreApi";

export type LoadState = "loading" | "ready" | "error";

export function useLeaderboard(difficulty: Difficulty, refreshKey = 0) {
  const [state, setState] = useState<LoadState>("loading");
  const [data, setData] = useState<LeaderboardData | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setState("loading");
    fetchLeaderboard(difficulty, 10, controller.signal)
      .then((payload) => {
        setData(payload);
        setState("ready");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        console.error("Failed to load leaderboard", error);
        setState("error");
      });
    return () => controller.abort();
  }, [difficulty, refreshKey]);

  return { state, data };
}

interface LeaderboardProps {
  difficulty: Difficulty;
  refreshKey: number;
  highlightId?: number | null;
}

export function Leaderboard({ difficulty, refreshKey, highlightId = null }: LeaderboardProps) {
  const { state, data } = useLeaderboard(difficulty, refreshKey);

  return (
    <section className="panel leaderboard" aria-labelledby="leaderboard-heading">
      <h2 id="leaderboard-heading" className="panel__title">
        لوحة الصدارة — {DIFFICULTIES[difficulty].label}
      </h2>

      {state === "loading" && <p className="leaderboard__hint">جارٍ تحميل النتائج…</p>}

      {state === "error" && (
        <p className="leaderboard__hint leaderboard__hint--error" role="status">
          تعذّر تحميل لوحة الصدارة. تأكد من تشغيل الخادم ثم أعد المحاولة.
        </p>
      )}

      {state === "ready" && data && data.entries.length === 0 && (
        <p className="leaderboard__hint">لا توجد نتائج بعد — كن أول من يسجّل!</p>
      )}

      {state === "ready" && data && data.entries.length > 0 && (
        <table className="leaderboard__table">
          <thead>
            <tr>
              <th scope="col">الترتيب</th>
              <th scope="col">اللاعب</th>
              <th scope="col">المحاولات</th>
              <th scope="col">الوقت</th>
            </tr>
          </thead>
          <tbody>
            {data.entries.map((entry) => (
              <tr
                key={entry.id}
                className={entry.id === highlightId ? "is-highlighted" : undefined}
              >
                <td>{toArabicDigits(entry.rank)}</td>
                <td>{entry.player_name}</td>
                <td>{toArabicDigits(entry.attempts)}</td>
                <td dir="ltr">{formatDuration(entry.duration_seconds)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
