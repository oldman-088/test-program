import type { Card as CardModel } from "../game/types";

interface CardProps {
  card: CardModel;
  faceUp: boolean;
  matched: boolean;
  disabled: boolean;
  onFlip: (cardId: string) => void;
}

export function Card({ card, faceUp, matched, disabled, onFlip }: CardProps) {
  const state = matched ? "matched" : faceUp ? "flipped" : "hidden";

  return (
    <button
      type="button"
      className={`card card--${state}`}
      onClick={() => onFlip(card.id)}
      disabled={disabled || matched || faceUp}
      aria-label={faceUp || matched ? `بطاقة ${card.symbol}` : "بطاقة مقلوبة"}
      aria-pressed={faceUp || matched}
      data-testid={`card-${card.id}`}
      data-state={state}
    >
      <span className="card__inner">
        <span className="card__face card__face--back" aria-hidden="true">
          ★
        </span>
        <span className="card__face card__face--front" aria-hidden="true">
          {card.symbol}
        </span>
      </span>
    </button>
  );
}
