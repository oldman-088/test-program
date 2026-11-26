import { useCallback, useEffect, useRef, useState } from "react";
import {
  DIFFICULTIES,
  buildResult,
  createBoard,
  flipCard,
  hideFlippedPair,
  isWon,
} from "../game/logic";
import type { BoardState, Difficulty, GameResult } from "../game/types";

const MISMATCH_DELAY_MS = 850;

interface UseGameOptions {
  random?: () => number;
  mismatchDelayMs?: number;
}

export type GameStatus = "idle" | "playing" | "won";

export interface UseGameResult {
  board: BoardState;
  difficulty: Difficulty;
  status: GameStatus;
  elapsedSeconds: number;
  result: GameResult | null;
  bestStreak: number;
  changeDifficulty: (difficulty: Difficulty) => void;
  start: () => void;
  restart: () => void;
  flip: (cardId: string) => void;
}

/**
 * Game state machine for the memory board.
 *
 * All transitions are computed outside React's state updaters (keeping them
 * pure for StrictMode double-invocation); the board lives in a ref as the
 * source of truth and is mirrored into state for rendering.
 */
export function useGame(options: UseGameOptions = {}): UseGameResult {
  const { mismatchDelayMs = MISMATCH_DELAY_MS } = options;
  const randomRef = useRef(options.random ?? Math.random);
  randomRef.current = options.random ?? Math.random;

  const [difficulty, setDifficulty] = useState<Difficulty>("easy");
  const [board, setBoard] = useState<BoardState>(() => createBoard(DIFFICULTIES.easy));
  const [status, setStatus] = useState<GameStatus>("idle");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [result, setResult] = useState<GameResult | null>(null);
  const [bestStreak, setBestStreak] = useState(0);

  const boardRef = useRef<BoardState>(board);
  const statusRef = useRef<GameStatus>(status);
  const difficultyRef = useRef<Difficulty>(difficulty);
  const streakRef = useRef(0);
  const bestStreakRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const startedAtRef = useRef<number | null>(null);

  const commitBoard = useCallback((next: BoardState) => {
    boardRef.current = next;
    setBoard(next);
  }, []);

  const commitStatus = useCallback((next: GameStatus) => {
    statusRef.current = next;
    setStatus(next);
  }, []);

  const clearTimers = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  const startClock = useCallback(() => {
    startedAtRef.current = Date.now();
    commitStatus("playing");
    timerRef.current = window.setInterval(() => {
      if (startedAtRef.current !== null) {
        setElapsedSeconds(Math.floor((Date.now() - startedAtRef.current) / 1000));
      }
    }, 250);
  }, [commitStatus]);

  const resetTo = useCallback(
    (nextDifficulty: Difficulty) => {
      clearTimers();
      startedAtRef.current = null;
      difficultyRef.current = nextDifficulty;
      setDifficulty(nextDifficulty);
      commitBoard(createBoard(DIFFICULTIES[nextDifficulty], randomRef.current));
      commitStatus("idle");
      setElapsedSeconds(0);
      setResult(null);
      streakRef.current = 0;
      bestStreakRef.current = 0;
      setBestStreak(0);
    },
    [clearTimers, commitBoard, commitStatus],
  );

  const start = useCallback(() => {
    if (statusRef.current !== "idle") {
      return;
    }
    startClock();
  }, [startClock]);

  const changeDifficulty = useCallback(
    (nextDifficulty: Difficulty) => {
      resetTo(nextDifficulty);
    },
    [resetTo],
  );

  const restart = useCallback(() => {
    resetTo(difficultyRef.current);
  }, [resetTo]);

  const flip = useCallback(
    (cardId: string) => {
      if (statusRef.current === "won") {
        return;
      }
      if (statusRef.current === "idle") {
        startClock();
      }

      const current = boardRef.current;
      if (current.flipped.length >= 2) {
        return;
      }

      const next = flipCard(current, cardId);
      if (next === current) {
        return;
      }

      if (next.matched.length > current.matched.length) {
        streakRef.current += 1;
        if (streakRef.current > bestStreakRef.current) {
          bestStreakRef.current = streakRef.current;
          setBestStreak(bestStreakRef.current);
        }
      } else if (next.misses > current.misses) {
        streakRef.current = 0;
      }

      if (isWon(next)) {
        const elapsed = startedAtRef.current
          ? Math.floor((Date.now() - startedAtRef.current) / 1000)
          : 0;
        clearTimers();
        setElapsedSeconds(elapsed);
        commitStatus("won");
        commitBoard(next);
        setResult(buildResult(next, difficultyRef.current, elapsed, bestStreakRef.current));
        return;
      }

      commitBoard(next);

      if (next.flipped.length === 2) {
        timeoutRef.current = window.setTimeout(() => {
          timeoutRef.current = null;
          const latest = boardRef.current;
          if (latest.flipped.length === 2) {
            commitBoard(hideFlippedPair(latest));
          }
        }, mismatchDelayMs);
      }
    },
    [clearTimers, commitBoard, commitStatus, mismatchDelayMs, startClock],
  );

  return {
    board,
    difficulty,
    status,
    elapsedSeconds,
    result,
    bestStreak,
    changeDifficulty,
    start,
    restart,
    flip,
  };
}
