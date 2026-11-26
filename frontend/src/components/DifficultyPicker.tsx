import { DIFFICULTY_LIST, toArabicDigits } from "../game/logic";
import type { Difficulty } from "../game/types";

interface DifficultyPickerProps {
  value: Difficulty;
  onChange: (difficulty: Difficulty) => void;
  disabled?: boolean;
}

export function DifficultyPicker({ value, onChange, disabled = false }: DifficultyPickerProps) {
  return (
    <fieldset className="difficulty" disabled={disabled}>
      <legend className="difficulty__legend">مستوى الصعوبة</legend>
      <div className="difficulty__options" role="radiogroup" aria-label="مستوى الصعوبة">
        {DIFFICULTY_LIST.map((config) => (
          <label
            key={config.id}
            className={`difficulty__option ${value === config.id ? "is-active" : ""}`}
          >
            <input
              type="radio"
              name="difficulty"
              value={config.id}
              checked={value === config.id}
              onChange={() => onChange(config.id)}
            />
            <span className="difficulty__label">{config.label}</span>
            <span className="difficulty__meta">
              {toArabicDigits(config.pairs)} أزواج
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
