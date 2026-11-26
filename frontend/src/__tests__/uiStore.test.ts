/**
 * The `uiStore` suite for the frontend test layer lives at
 * `src/store/uiStore.test.ts` (next to the store it covers).
 *
 * This former location is kept as a one-line entry point so the original
 * command still works:
 *   npx vitest run src/__tests__/uiStore.test.ts
 * Both paths share the same tests — nothing is asserted twice.
 */
import '../store/uiStore.test';
