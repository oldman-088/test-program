import type { CSSProperties } from "react";
import type { BoardState, DifficultyConfig } from "../game/types";
import { Card } from "./Card";

interface BoardProps {
  board: BoardState;
  config: DifficultyConfig;
  locked: boolean;
  onFlip: (cardId: string) => void;
}

export function Board({ board, config, locked, onFlip }: BoardProps) {
  const style = { "--board-columns": config.columns } as CSSProperties;

  return (
    <div
      className={`board board--${config.id}`}
      style={style}
      role="grid"
      aria-label={`لوحة بطاقات المستوى ${config.label}`}
    >
      {board.cards.map((card) => (
        <Card
          key={card.id}
          card={card}
          faceUp={board.flipped.includes(card.id)}
          matched={board.matched.includes(card.id)}
          disabled={locked}
          onFlip={onFlip}
        />
      ))}
    </div>
  );
}
