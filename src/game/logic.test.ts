import { describe, it, expect } from 'vitest';
import {
  createInitialGameState,
  flipCard,
  resolveTurn,
  canFlipCard,
} from './logic';

const identityShuffle = <T,>(items: T[]): T[] => items;

describe('Memory Card Game Logic', () => {
  it('creates the correct number of cards for each difficulty', () => {
    const easy = createInitialGameState('easy', identityShuffle);
    const normal = createInitialGameState('normal', identityShuffle);
    const hard = createInitialGameState('hard', identityShuffle);

    expect(easy.cards).toHaveLength(12);
    expect(easy.totalPairs).toBe(6);

    expect(normal.cards).toHaveLength(16);
    expect(normal.totalPairs).toBe(8);

    expect(hard.cards).toHaveLength(24);
    expect(hard.totalPairs).toBe(12);
  });

  it('locks selection after flipping two cards and increments attempts', () => {
    let state = createInitialGameState('easy', identityShuffle);

    state = flipCard(state, state.cards[0].id);
    expect(state.flippedIds).toHaveLength(1);
    expect(state.attempts).toBe(0);
    expect(state.isLocked).toBe(false);

    state = flipCard(state, state.cards[2].id);
    expect(state.flippedIds).toHaveLength(2);
    expect(state.attempts).toBe(1);
    expect(state.isLocked).toBe(true);

    // Cannot flip a third card while locked
    expect(canFlipCard(state, state.cards[4].id)).toBe(false);
  });

  it('detects a match, keeps cards revealed, and completes the game when all pairs match', () => {
    let state = createInitialGameState('easy', identityShuffle);

    // Match all 6 pairs sequentially (identityShuffle places pairs at [0,1], [2,3], ...)
    for (let i = 0; i < state.cards.length; i += 2) {
      state = flipCard(state, state.cards[i].id);
      state = flipCard(state, state.cards[i + 1].id);
      state = resolveTurn(state);
    }

    expect(state.matchedPairs).toBe(6);
    expect(state.attempts).toBe(6);
    expect(state.isCompleted).toBe(true);
    expect(state.isLocked).toBe(false);
    expect(state.cards.every((c) => c.isMatched && c.isFlipped)).toBe(true);
  });

  it('flips mismatched cards back face-down and unlocks the board', () => {
    let state = createInitialGameState('easy', identityShuffle);

    // cards[0] is sun-a, cards[2] is moon-a -> mismatch
    state = flipCard(state, state.cards[0].id);
    state = flipCard(state, state.cards[2].id);
    state = resolveTurn(state);

    expect(state.matchedPairs).toBe(0);
    expect(state.attempts).toBe(1);
    expect(state.isLocked).toBe(false);
    expect(state.flippedIds).toHaveLength(0);
    expect(state.cards[0].isFlipped).toBe(false);
    expect(state.cards[2].isFlipped).toBe(false);
  });
});
