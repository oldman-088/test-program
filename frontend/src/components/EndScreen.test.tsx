import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { GameResult } from "../game/types";
import { EndScreen } from "./EndScreen";

const RESULT: GameResult = {
  difficulty: "easy",
  attempts: 9,
  misses: 3,
  moves: 15,
  durationSeconds: 74,
  accuracy: 67,
  bestStreak: 2,
};

function renderEndScreen(overrides: Partial<GameResult> = {}) {
  const onScoreSaved = vi.fn();
  const onPlayAgain = vi.fn();
  const onChangeDifficulty = vi.fn();
  render(
    <EndScreen
      result={{ ...RESULT, ...overrides }}
      onScoreSaved={onScoreSaved}
      onPlayAgain={onPlayAgain}
      onChangeDifficulty={onChangeDifficulty}
    />,
  );
  return { onScoreSaved, onPlayAgain, onChangeDifficulty };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("EndScreen", () => {
  it("summarises the round in Arabic digits", () => {
    renderEndScreen();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("٩")).toBeInTheDocument();
    expect(screen.getByText("٦٧٪")).toBeInTheDocument();
    expect(screen.getByText("01:14")).toBeInTheDocument();
  });

  it("disables saving until a name is entered", async () => {
    const user = userEvent.setup();
    renderEndScreen();

    const save = screen.getByRole("button", { name: "احفظ النتيجة" });
    expect(save).toBeDisabled();

    await user.type(screen.getByLabelText("اسم اللاعب"), "   ");
    expect(save).toBeDisabled();

    await user.type(screen.getByLabelText("اسم اللاعب"), "ليلى");
    expect(save).toBeEnabled();
  });

  it("submits the score and reports the new id", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: () => Promise.resolve({ id: 42 }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const { onScoreSaved } = renderEndScreen();

    await user.type(screen.getByLabelText("اسم اللاعب"), "  ليلى  ");
    await user.click(screen.getByRole("button", { name: "احفظ النتيجة" }));

    await waitFor(() => expect(onScoreSaved).toHaveBeenCalledWith(42));
    expect(await screen.findByText(/تم حفظ نتيجتك/)).toBeInTheDocument();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(String(init.body)) as Record<string, unknown>;
    expect(body).toMatchObject({
      player_name: "ليلى",
      difficulty: "easy",
      attempts: 9,
      duration_seconds: 74,
    });
    expect(body["finished_at"]).toEqual(expect.any(String));
  });

  it("never submits zero attempts or zero duration", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: () => Promise.resolve({ id: 1 }),
    });
    vi.stubGlobal("fetch", fetchMock);
    renderEndScreen({ attempts: 0, durationSeconds: 0 });

    await user.type(screen.getByLabelText("اسم اللاعب"), "عمر");
    await user.click(screen.getByRole("button", { name: "احفظ النتيجة" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toMatchObject({
      attempts: 1,
      duration_seconds: 1,
    });
  });

  it("shows an error and stays retryable when saving fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500, json: () => Promise.resolve({}) }),
    );
    const { onScoreSaved } = renderEndScreen();

    await user.type(screen.getByLabelText("اسم اللاعب"), "ليلى");
    await user.click(screen.getByRole("button", { name: "احفظ النتيجة" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/تعذّر حفظ النتيجة/);
    expect(onScoreSaved).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "احفظ النتيجة" })).toBeEnabled();
  });

  it("exposes restart actions", async () => {
    const user = userEvent.setup();
    const { onPlayAgain, onChangeDifficulty } = renderEndScreen();

    await user.click(screen.getByRole("button", { name: "العب مرة أخرى" }));
    await user.click(screen.getByRole("button", { name: "تغيير المستوى" }));

    expect(onPlayAgain).toHaveBeenCalledTimes(1);
    expect(onChangeDifficulty).toHaveBeenCalledTimes(1);
  });
});
