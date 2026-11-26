import { describe, expect, it } from "vitest";
import {
  DIFFICULTIES,
  accuracyOf,
  buildDeck,
  buildResult,
  createBoard,
  flipCard,
  formatDuration,
  hideFlippedPair,
  isWon,
  shuffle,
  toArabicDigits,
} from "./logic";

/** Deterministic RNG so deck order is stable. */
function seeded(seed = 42): () => number {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 2 ** 32;
    return state / 2 ** 32;
  };
}

describe("shuffle", () => {
  it("keeps every element exactly once", () => {
    const source = [1, 2, 3, 4, 5, 6];
    const result = shuffle(source, seeded(7));
    expect(result).toHaveLength(source.length);
    expect([...result].sort()).toEqual([...source].sort());
  });

  it("does not mutate the input", () => {
    const source = Object.freeze([1, 2, 3]);
    expect(shuffle(source)).toHaveLength(3);
    expect(source).toEqual([1, 2, 3]);
  });
});

describe("buildDeck", () => {
  it.each(Object.values(DIFFICULTIES))("creates %s pairs of unique cards", (config) => {
    const deck = buildDeck(config, seeded());
    expect(deck).toHaveLength(config.pairs * 2);
    expect(new Set(deck.map((card) => card.id)).size).toBe(config.pairs * 2);

    const counts = new Map<string, number>();
    for (const card of deck) {
      counts.set(card.pairId, (counts.get(card.pairId) ?? 0) + 1);
    }
    expect([...counts.values()].every((count) => count === 2)).toBe(true);
  });

  it("throws when the emoji pool is too small", () => {
    expect(() =>
      buildDeck({ ...DIFFICULTIES.easy, pairs: 12, emojiPool: "🍎🍌" }),
    ).toThrow(/needs 12 symbols/);
  });
});

describe("flipCard", () => {
  it("reveals a single card without counting an attempt", () => {
    const board = createBoard(DIFFICULTIES.easy, seeded());
    const first = board.cards[0]!;
    const next = flipCard(board, first.id);

    expect(next.flipped).toEqual([first.id]);
    expect(next.attempts).toBe(0);
    expect(next.moves).toBe(1);
  });

  it("marks a matching pair and clears flipped", () => {
    const board = createBoard(DIFFICULTIES.easy, seeded());
    const first = board.cards[0]!;
    const partner = board.cards.find((card) => card.pairId === first.pairId && card.id !== first.id)!;

    const afterFirst = flipCard(board, first.id);
    const afterSecond = flipCard(afterFirst, partner.id);

    expect(afterSecond.matched).toEqual([first.id, partner.id]);
    expect(afterSecond.flipped).toEqual([]);
    expect(afterSecond.attempts).toBe(1);
    expect(afterSecond.misses).toBe(0);
  });

  it("counts a mismatch and can be hidden again", () => {
    const board = createBoard(DIFFICULTIES.easy, seeded());
    const first = board.cards[0]!;
    const other = board.cards.find((card) => card.pairId !== first.pairId)!;

    const afterFirst = flipCard(board, first.id);
    const afterSecond = flipCard(afterFirst, other.id);

    expect(afterSecond.flipped).toHaveLength(2);
    expect(afterSecond.attempts).toBe(1);
    expect(afterSecond.misses).toBe(1);

    const hidden = hideFlippedPair(afterSecond);
    expect(hidden.flipped).toEqual([]);
    expect(hidden.matched).toEqual([]);
  });

  it("ignores repeat clicks, matched cards, and a third card", () => {
    const board = createBoard(DIFFICULTIES.easy, seeded());
    const first = board.cards[0]!;
    const other = board.cards.find((card) => card.pairId !== first.pairId)!;
    const third = board.cards.find(
      (card) => card.id !== first.id && card.id !== other.id,
    )!;

    const afterFirst = flipCard(board, first.id);
    expect(flipCard(afterFirst, first.id)).toBe(afterFirst);

    const afterSecond = flipCard(afterFirst, other.id);
    expect(flipCard(afterSecond, third.id)).toBe(afterSecond);

    const partner = board.cards.find(
      (card) => card.pairId === first.pairId && card.id !== first.id,
    )!;
    const hidden = hideFlippedPair(afterSecond);
    const matched = flipCard(flipCard(hidden, first.id), partner.id);
    expect(flipCard(matched, first.id)).toBe(matched);
    expect(flipCard(matched, partner.id)).toBe(matched);
  });
});

describe("winning", () => {
  it("is won only when every card is matched", () => {
    let board = createBoard(DIFFICULTIES.easy, seeded(11));
    const pairs = new Map<string, string[]>();
    for (const card of board.cards) {
      pairs.set(card.pairId, [...(pairs.get(card.pairId) ?? []), card.id]);
    }

    let safety = 0;
    while (!isWon(board) && safety < 100) {
      const unmatchedPair = [...pairs.values()].find((ids) => !board.matched.includes(ids[0]!))!;
      board = flipCard(board, unmatchedPair[0]!);
      board = flipCard(board, unmatchedPair[1]!);
      safety += 1;
    }

    expect(isWon(board)).toBe(true);
    expect(board.matched).toHaveLength(DIFFICULTIES.easy.pairs * 2);
    expect(board.attempts).toBe(DIFFICULTIES.easy.pairs);
    expect(accuracyOf(board)).toBe(100);
  });

  it("an empty board is never won", () => {
    expect(isWon({ ...createBoard(DIFFICULTIES.easy), cards: [] })).toBe(false);
  });
});

describe("formatting", () => {
  it("formats durations as mm:ss", () => {
    expect(formatDuration(0)).toBe("00:00");
    expect(formatDuration(9)).toBe("00:09");
    expect(formatDuration(75)).toBe("01:15");
    expect(formatDuration(600)).toBe("10:00");
    expect(formatDuration(-5)).toBe("00:00");
  });

  it("converts digits to Arabic-Indic", () => {
    expect(toArabicDigits(0)).toBe("٠");
    expect(toArabicDigits(123)).toBe("١٢٣");
  });

  it("computes accuracy with no attempts as zero", () => {
    expect(accuracyOf(createBoard(DIFFICULTIES.easy))).toBe(0);
  });

  it("builds a result snapshot", () => {
    const board = { ...createBoard(DIFFICULTIES.hard), attempts: 20, misses: 5 };
    const result = buildResult(board, "hard", 93, 4);
    expect(result).toMatchObject({
      difficulty: "hard",
      attempts: 20,
      misses: 5,
      durationSeconds: 93,
      accuracy: 75,
      bestStreak: 4,
    });
  });
});
