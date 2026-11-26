export type Difficulty = "easy" | "medium" | "hard";

export interface DifficultyConfig {
  id: Difficulty;
  label: string;
  /** Number of pairs, i.e. half the cards on the board. */
  pairs: number;
  columns: number;
  emojiPool: string;
}

export interface Card {
  /** Unique per card instance, e.g. "p3-1". */
  id: string;
  /** Pair identifier shared by two cards. */
  pairId: string;
  symbol: string;
}

export interface BoardState {
  cards: Card[];
  /** Ids of cards currently face up. */
  flipped: string[];
  /** Ids of cards that are matched and stay face up. */
  matched: string[];
  /** Reveal attempts: incremented once per completed pair flip. */
  attempts: number;
  /** Attempts that ended in a mismatch. */
  misses: number;
  moves: number;
}

export interface GameResult {
  difficulty: Difficulty;
  attempts: number;
  misses: number;
  moves: number;
  durationSeconds: number;
  accuracy: number;
  bestStreak: number;
}
