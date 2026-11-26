/** Minimal `cn` helper (clsx + tailwind-merge without extra deps). */
export function cn(...inputs: Array<string | false | null | undefined>): string {
  return inputs.filter(Boolean).join(' ');
}
