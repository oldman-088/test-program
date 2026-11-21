export type Difficulty = 'easy' | 'normal' | 'hard';

export interface DifficultyConfig {
  id: Difficulty;
  cols: number;
  rows: number;
  totalPairs: number;
}

export interface CardItem {
  id: string;
  pairId: string;
  symbol: string;
  label: string;
  isFlipped: boolean;
  isMatched: boolean;
}

export interface GameState {
  difficulty: Difficulty;
  cards: CardItem[];
  flippedIds: string[];
  attempts: number;
  matchedPairs: number;
  totalPairs: number;
  isLocked: boolean;
  isCompleted: boolean;
}

export interface ScorePayload {
  attempts: number;
  seconds: number;
  playerName: string;
  difficulty: Difficulty;
}
