import type { BoardState, Card, Difficulty, DifficultyConfig, GameResult } from "./types";

export const DIFFICULTIES: Record<Difficulty, DifficultyConfig> = {
  easy: {
    id: "easy",
    label: "سهل",
    pairs: 6,
    columns: 4,
    emojiPool: "🍎🍌🍇🍓🍊🍉",
  },
  medium: {
    id: "medium",
    label: "متوسط",
    pairs: 8,
    columns: 4,
    emojiPool: "🍎🍌🍇🍓🍊🍉🍒🥝",
  },
  hard: {
    id: "hard",
    label: "صعب",
    pairs: 12,
    columns: 6,
    emojiPool: "🍎🍌🍇🍓🍊🍉🍒🥝🍍🥥🌽🍋",
  },
};

export const DIFFICULTY_LIST: DifficultyConfig[] = [
  DIFFICULTIES.easy,
  DIFFICULTIES.medium,
  DIFFICULTIES.hard,
];

/** Fisher–Yates shuffle. Accepts an RNG so tests can be deterministic. */
export function shuffle<T>(items: readonly T[], random: () => number = Math.random): T[] {
  const result = [...items];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    const current = result[index] as T;
    result[index] = result[swapIndex] as T;
    result[swapIndex] = current;
  }
  return result;
}

export function buildDeck(config: DifficultyConfig, random: () => number = Math.random): Card[] {
  const symbols = Array.from(config.emojiPool);
  if (symbols.length < config.pairs) {
    throw new Error(`Difficulty "${config.id}" needs ${config.pairs} symbols`);
  }

  const pairs = symbols.slice(0, config.pairs).flatMap((symbol, index) => {
    const pairId = `p${index}`;
    return [0, 1].map((copy) => ({ id: `${pairId}-${copy}`, pairId, symbol }));
  });

  return shuffle(pairs, random);
}

export function createBoard(
  config: DifficultyConfig,
  random: () => number = Math.random,
): BoardState {
  return {
    cards: buildDeck(config, random),
    flipped: [],
    matched: [],
    attempts: 0,
    misses: 0,
    moves: 0,
  };
}

export function isWon(board: BoardState): boolean {
  return board.cards.length > 0 && board.matched.length === board.cards.length;
}

export function accuracyOf(board: BoardState): number {
  if (board.attempts === 0) {
    return 0;
  }
  return Math.round(((board.attempts - board.misses) / board.attempts) * 100);
}

/**
 * Reveal a card. Pure: returns the next board state.
 *
 * - Clicking an already flipped/matched card is a no-op.
 * - The first card of a pair is revealed; the second completes an attempt.
 * - A match moves both cards to `matched` (they stay face up).
 * - A mismatch leaves both in `flipped` so the UI can animate them back;
 *   the caller schedules `hideFlippedPair`.
 * - At most two cards are face up at a time.
 */
export function flipCard(board: BoardState, cardId: string): BoardState {
  const card = board.cards.find((candidate) => candidate.id === cardId);
  if (!card || board.flipped.includes(cardId) || board.matched.includes(cardId)) {
    return board;
  }
  if (board.flipped.length >= 2) {
    return board;
  }

  const flipped = [...board.flipped, cardId];
  const moves = board.moves + 1;

  if (flipped.length === 1) {
    return { ...board, flipped, moves };
  }

  const firstCard = board.cards.find((candidate) => candidate.id === flipped[0]);
  const attempts = board.attempts + 1;

  if (firstCard && firstCard.pairId === card.pairId) {
    return {
      ...board,
      flipped: [],
      matched: [...board.matched, firstCard.id, cardId],
      attempts,
      moves,
    };
  }

  return { ...board, flipped, attempts, misses: board.misses + 1, moves };
}

/** Turn a mismatched pair face down again. */
export function hideFlippedPair(board: BoardState): BoardState {
  if (board.flipped.length < 2) {
    return board;
  }
  return { ...board, flipped: [] };
}

export function buildResult(
  board: BoardState,
  difficulty: Difficulty,
  durationSeconds: number,
  bestStreak = 0,
): GameResult {
  return {
    difficulty,
    attempts: board.attempts,
    misses: board.misses,
    moves: board.moves,
    durationSeconds,
    accuracy: accuracyOf(board),
    bestStreak,
  };
}

export function formatDuration(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

const ARABIC_DIGITS = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"];

/** Render Western numerals as Arabic-Indic digits for display. */
export function toArabicDigits(value: number | string): string {
  return String(value).replace(/\d/g, (digit) => ARABIC_DIGITS[Number(digit)] ?? digit);
}
