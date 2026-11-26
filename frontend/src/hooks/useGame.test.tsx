import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DIFFICULTIES } from "../game/logic";
import type { Difficulty } from "../game/types";
import { useGame } from "./useGame";

function seeded(seed = 3): () => number {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 2 ** 32;
    return state / 2 ** 32;
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-11-26T10:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

function pairsOf(cards: { id: string; pairId: string }[]): string[][] {
  const groups = new Map<string, string[]>();
  for (const card of cards) {
    groups.set(card.pairId, [...(groups.get(card.pairId) ?? []), card.id]);
  }
  return [...groups.values()];
}

describe("useGame", () => {
  it("starts idle with a hidden board", () => {
    const { result } = renderHook(() => useGame({ random: seeded() }));
    expect(result.current.status).toBe("idle");
    expect(result.current.board.cards).toHaveLength(DIFFICULTIES.easy.pairs * 2);
    expect(result.current.board.matched).toHaveLength(0);
    expect(result.current.elapsedSeconds).toBe(0);
  });

  it("starts the clock on the first flip", () => {
    const { result } = renderHook(() => useGame({ random: seeded() }));
    const firstId = result.current.board.cards[0]!.id;

    act(() => result.current.flip(firstId));
    expect(result.current.status).toBe("playing");

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(result.current.elapsedSeconds).toBe(3);
  });

  it("hides a mismatched pair after the delay", () => {
    const { result } = renderHook(() =>
      useGame({ random: seeded(), mismatchDelayMs: 500 }),
    );
    const cards = result.current.board.cards;
    const pairs = pairsOf(cards);
    const first = cards.find((card) => card.pairId === pairs[0]![0]!.slice(0, -2))!;
    const foreign = cards.find((card) => card.pairId !== first.pairId)!;

    act(() => result.current.flip(first.id));
    act(() => result.current.flip(foreign.id));
    expect(result.current.board.flipped).toHaveLength(2);
    expect(result.current.board.misses).toBe(1);

    act(() => {
      vi.advanceTimersByTime(600);
    });
    expect(result.current.board.flipped).toHaveLength(0);
  });

  it("wins when every pair is matched and reports the result", () => {
    const { result } = renderHook(() => useGame({ random: seeded(21) }));

    const pairs = pairsOf(result.current.board.cards);
    // Clock starts on the first flip, five seconds before finishing the round.
    act(() => result.current.flip(pairs[0]![0]!));
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    for (const pair of pairs) {
      for (const cardId of pair) {
        act(() => result.current.flip(cardId));
      }
    }

    expect(result.current.status).toBe("won");
    const winResult = result.current.result;
    expect(winResult).not.toBeNull();
    expect(winResult?.attempts).toBe(DIFFICULTIES.easy.pairs);
    expect(winResult?.misses).toBe(0);
    expect(winResult?.accuracy).toBe(100);
    expect(winResult?.bestStreak).toBe(DIFFICULTIES.easy.pairs);
    expect(winResult?.durationSeconds).toBe(5);
  });

  it("ignores clicks after winning", () => {
    const { result } = renderHook(() => useGame({ random: seeded(5) }));
    const pairs = pairsOf(result.current.board.cards);
    for (const pair of pairs) {
      act(() => result.current.flip(pair[0]!));
      act(() => result.current.flip(pair[1]!));
    }
    expect(result.current.status).toBe("won");

    const before = result.current.board;
    act(() => result.current.flip(pairs[0]![0]!));
    expect(result.current.board).toBe(before);
  });

  it.each(["easy", "medium", "hard"] as Difficulty[])(
    "switching to %s rebuilds the board with the right size",
    (difficulty) => {
      const { result } = renderHook(() => useGame({ random: seeded(9) }));
      act(() => result.current.changeDifficulty(difficulty));

      expect(result.current.difficulty).toBe(difficulty);
      expect(result.current.status).toBe("idle");
      expect(result.current.board.cards).toHaveLength(DIFFICULTIES[difficulty].pairs * 2);
    },
  );

  it("restart deals a fresh board and clears the result", () => {
    const { result } = renderHook(() => useGame({ random: seeded(13) }));
    act(() => result.current.flip(result.current.board.cards[0]!.id));
    act(() => result.current.restart());

    expect(result.current.status).toBe("idle");
    expect(result.current.board.flipped).toHaveLength(0);
    expect(result.current.board.moves).toBe(0);
    expect(result.current.result).toBeNull();
    expect(result.current.elapsedSeconds).toBe(0);
  });
});
