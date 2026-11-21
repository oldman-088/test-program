import React from 'react';
import { CardItem } from '../game/types';
import { AppStrings } from '../i18n/strings';

interface CardProps {
  card: CardItem;
  disabled: boolean;
  onFlip: (id: string) => void;
  strings: AppStrings;
}

export const Card: React.FC<CardProps> = ({ card, disabled, onFlip, strings }) => {
  const isRevealed = card.isFlipped || card.isMatched;

  const ariaLabel = card.isMatched
    ? `${card.label} - ${strings.card.matchedLabel}`
    : isRevealed
      ? card.label
      : strings.card.hiddenLabel;

  return (
    <button
      type="button"
      onClick={() => onFlip(card.id)}
      disabled={disabled || isRevealed}
      aria-label={ariaLabel}
      aria-pressed={isRevealed}
      className="group relative aspect-square w-full perspective-1000 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 rounded-xl"
    >
      <div
        className={`relative h-full w-full duration-500 preserve-3d transition-transform ${
          isRevealed ? 'rotate-y-180' : 'group-hover:-translate-y-0.5'
        }`}
      >
        {/* Face-down (back of card) */}
        <div
          className="absolute inset-0 flex items-center justify-center rounded-xl border border-slate-700/80 bg-gradient-to-br from-slate-800 to-slate-900 shadow-md backface-hidden"
        >
          <span className="text-2xl font-bold text-indigo-400/70 select-none">؟</span>
        </div>

        {/* Face-up (front of card) */}
        <div
          className={`absolute inset-0 flex flex-col items-center justify-center gap-1 rounded-xl border shadow-lg backface-hidden rotate-y-180 transition-colors ${
            card.isMatched
              ? 'border-emerald-500/70 bg-emerald-950/60 text-emerald-100'
              : 'border-indigo-500/70 bg-slate-800 text-slate-100'
          }`}
        >
          <span className="text-3xl sm:text-4xl leading-none select-none" aria-hidden="true">
            {card.symbol}
          </span>
          <span className="text-[11px] sm:text-xs font-medium text-slate-300 select-none">
            {card.label}
          </span>
        </div>
      </div>
    </button>
  );
};
