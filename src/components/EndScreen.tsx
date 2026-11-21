import React, { useState } from 'react';
import { Trophy, RotateCcw, Send, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Difficulty } from '../game/types';
import { AppStrings } from '../i18n/strings';
import { submitScore } from '../services/scoreApi';

interface EndScreenProps {
  attempts: number;
  seconds: number;
  difficulty: Difficulty;
  onPlayAgain: () => void;
  strings: AppStrings;
}

export const EndScreen: React.FC<EndScreenProps> = ({
  attempts,
  seconds,
  difficulty,
  onPlayAgain,
  strings,
}) => {
  const [playerName, setPlayerName] = useState('');
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitStatus === 'submitting' || submitStatus === 'success') {
      return;
    }

    setSubmitStatus('submitting');
    const result = await submitScore({
      attempts,
      seconds,
      playerName: playerName.trim() || 'لاعب',
      difficulty,
    });

    setSubmitStatus(result.ok ? 'success' : 'error');
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="end-screen-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-700/80 bg-slate-900 p-6 shadow-2xl">
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
            <Trophy className="h-7 w-7" />
          </div>
          <h2 id="end-screen-title" className="text-xl font-bold text-white">
            {strings.endScreen.congratsTitle}
          </h2>
          <p className="mt-1 text-sm text-slate-400">{strings.endScreen.congratsSubtitle}</p>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="text-xs text-slate-400">{strings.stats.attempts}</div>
            <div className="mt-1 text-lg font-bold text-indigo-400">{attempts}</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="text-xs text-slate-400">{strings.stats.time}</div>
            <div className="mt-1 text-lg font-bold text-emerald-400">
              {seconds} {strings.stats.secondsUnit}
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="text-xs text-slate-400">{strings.difficultyLabel}</div>
            <div className="mt-1 text-sm font-semibold text-slate-200">
              {strings.difficulties[difficulty]}
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-3">
          <div>
            <label htmlFor="player-name" className="block text-start text-xs font-medium text-slate-300 mb-1.5">
              {strings.endScreen.playerNameLabel}
            </label>
            <input
              id="player-name"
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder={strings.endScreen.playerNamePlaceholder}
              disabled={submitStatus === 'success'}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
            />
          </div>

          {submitStatus === 'success' && (
            <div
              role="status"
              className="flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-950/50 px-3 py-2 text-xs text-emerald-300"
            >
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{strings.endScreen.scoreSentSuccess}</span>
            </div>
          )}

          {submitStatus === 'error' && (
            <div
              role="alert"
              className="flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-950/50 px-3 py-2 text-xs text-amber-300"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{strings.endScreen.scoreSentError}</span>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-2.5 pt-2">
            <button
              type="submit"
              disabled={submitStatus === 'submitting' || submitStatus === 'success'}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              <span>
                {submitStatus === 'submitting'
                  ? strings.actions.submittingScore
                  : strings.actions.submitScore}
              </span>
            </button>

            <button
              type="button"
              onClick={onPlayAgain}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500"
            >
              <RotateCcw className="h-4 w-4" />
              <span>{strings.actions.playAgain}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
