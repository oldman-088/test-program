import { useEffect } from 'react';
import { useUiStore } from '../store/uiStore';
import type { Direction } from '../lib/i18n';

/**
 * Applies the current direction (and locale) to <html>:
 * sets `dir` (rtl/ltr) and `lang`. Returns the active direction.
 */
export function useDirection(): Direction {
  const direction = useUiStore((s) => s.direction);
  const locale = useUiStore((s) => s.locale);

  useEffect(() => {
    document.documentElement.dir = direction;
    document.documentElement.lang = locale;
  }, [direction, locale]);

  return direction;
}
