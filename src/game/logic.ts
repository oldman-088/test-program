import { CardItem, Difficulty, DifficultyConfig, GameState } from './types';

export const DIFFICULTY_CONFIGS: Record<Difficulty, DifficultyConfig> = {
  easy: { id: 'easy', cols: 4, rows: 3, totalPairs: 6 },
  normal: { id: 'normal', cols: 4, rows: 4, totalPairs: 8 },
  hard: { id: 'hard', cols: 6, rows: 4, totalPairs: 12 },
};

export const CARD_SYMBOLS: ReadonlyArray<{ pairId: string; symbol: string; label: string }> = [
  { pairId: 'sun', symbol: '☀️', label: 'شمس' },
  { pairId: 'moon', symbol: '🌙', label: 'قمر' },
  { pairId: 'star', symbol: '⭐', label: 'نجمة' },
  { pairId: 'tree', symbol: '🌴', label: 'نخلة' },
  { pairId: 'flower', symbol: '🌺', label: 'زهرة' },
  { pairId: 'fire', symbol: '🔥', label: 'نار' },
  { pairId: 'wave', symbol: '🌊', label: 'موجة' },
  { pairId: 'gem', symbol: '💎', label: 'جوهرة' },
  { pairId: 'crown', symbol: '👑', label: 'تاج' },
  { pairId: 'rocket', symbol: '🚀', label: 'صاروخ' },
  { pairId: 'compass', symbol: '🧭', label: 'بوصلة' },
  { pairId: 'book', symbol: '📖', label: 'كتاب' },
];

export function shuffleArray<T>(items: T[], randomFn: () => number = Math.random): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(randomFn() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

export function createDeck(
  difficulty: Difficulty,
  shuffleFn: <T>(items: T[]) => T[] = shuffleArray
): CardItem[] {
  const { totalPairs } = DIFFICULTY_CONFIGS[difficulty];
  const selectedSymbols = CARD_SYMBOLS.slice(0, totalPairs);

  const deck: CardItem[] = selectedSymbols.flatMap((item) => [
    {
      id: `${item.pairId}-a`,
      pairId: item.pairId,
      symbol: item.symbol,
      label: item.label,
      isFlipped: false,
      isMatched: false,
    },
    {
      id: `${item.pairId}-b`,
      pairId: item.pairId,
      symbol: item.symbol,
      label: item.label,
      isFlipped: false,
      isMatched: false,
    },
  ]);

  return shuffleFn(deck);
}

export function createInitialGameState(
  difficulty: Difficulty = 'normal',
  shuffleFn: <T>(items: T[]) => T[] = shuffleArray
): GameState {
  const { totalPairs } = DIFFICULTY_CONFIGS[difficulty];
  return {
    difficulty,
    cards: createDeck(difficulty, shuffleFn),
    flippedIds: [],
    attempts: 0,
    matchedPairs: 0,
    totalPairs,
    isLocked: false,
    isCompleted: false,
  };
}

export function canFlipCard(state: GameState, cardId: string): boolean {
  if (state.isLocked || state.isCompleted) {
    return false;
  }
  const card = state.cards.find((c) => c.id === cardId);
  if (!card || card.isFlipped || card.isMatched) {
    return false;
  }
  return true;
}

export function flipCard(state: GameState, cardId: string): GameState {
  if (!canFlipCard(state, cardId)) {
    return state;
  }

  const updatedCards = state.cards.map((card) =>
    card.id === cardId ? { ...card, isFlipped: true } : card
  );
  const nextFlippedIds = [...state.flippedIds, cardId];
  const isTurnComplete = nextFlippedIds.length === 2;

  return {
    ...state,
    cards: updatedCards,
    flippedIds: nextFlippedIds,
    attempts: isTurnComplete ? state.attempts + 1 : state.attempts,
    isLocked: isTurnComplete,
  };
}

export function resolveTurn(state: GameState): GameState {
  if (state.flippedIds.length !== 2) {
    return state;
  }

  const [firstId, secondId] = state.flippedIds;
  const firstCard = state.cards.find((c) => c.id === firstId);
  const secondCard = state.cards.find((c) => c.id === secondId);

  if (!firstCard || !secondCard) {
    return { ...state, flippedIds: [], isLocked: false };
  }

  const isMatch = firstCard.pairId === secondCard.pairId;

  const updatedCards = state.cards.map((card) => {
    if (card.id !== firstId && card.id !== secondId) {
      return card;
    }
    if (isMatch) {
      return { ...card, isMatched: true, isFlipped: true };
    }
    return { ...card, isFlipped: false };
  });

  const nextMatchedPairs = isMatch ? state.matchedPairs + 1 : state.matchedPairs;
  const isCompleted = nextMatchedPairs === state.totalPairs;

  return {
    ...state,
    cards: updatedCards,
    flippedIds: [],
    matchedPairs: nextMatchedPairs,
    isLocked: false,
    isCompleted,
  };
}
