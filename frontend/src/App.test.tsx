import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const EMPTY_BOARD = { difficulty: "easy", limit: 10, total: 0, entries: [] };

function stubApi(overrides: Partial<Record<"leaderboard" | "scores", unknown>> = {}) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.startsWith("/api/v1/leaderboard")) {
      const body = overrides.leaderboard ?? { ...EMPTY_BOARD, difficulty: "easy" };
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
    }
    if (url === "/api/v1/scores") {
      const body =
        overrides.scores ??
        ({
          id: 99,
          player_name: "لاعب",
          difficulty: "easy",
          attempts: 6,
          duration_seconds: 12,
          finished_at: "2026-11-26T00:00:00Z",
          rank: 1,
        } as unknown);
      return Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve(body) });
    }
    return Promise.reject(new Error(`Unexpected request: ${url}`));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  stubApi();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("App", () => {
  it("renders the Arabic RTL layout with the board and empty leaderboard", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: "تطابق البطاقات" })).toBeInTheDocument();
    expect(screen.getByRole("grid", { name: /لوحة بطاقات/ })).toBeInTheDocument();
    expect(await screen.findByText(/لا توجد نتائج بعد/)).toBeInTheDocument();
    expect(screen.getAllByTestId(/^card-/)).toHaveLength(12);
  });

  it("switches difficulty and rebuilds the board", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getAllByTestId(/^card-/)).toHaveLength(12);

    await user.click(screen.getByRole("radio", { name: /صعب/ }));

    await waitFor(() => expect(screen.getAllByTestId(/^card-/)).toHaveLength(24));
    expect(screen.getByRole("radio", { name: /صعب/ })).toBeChecked();
  });

  it("flips cards on click", async () => {
    const user = userEvent.setup();
    render(<App />);

    const cards = screen.getAllByTestId(/^card-/);
    const first = cards[0]!;
    expect(first).toHaveAttribute("data-state", "hidden");

    await user.click(first);

    expect(first).toHaveAttribute("data-state", "flipped");
    expect(first).toBeDisabled();
  });

  it("shows the leaderboard rows returned by the API", async () => {
    stubApi({
      leaderboard: {
        difficulty: "easy",
        limit: 10,
        total: 1,
        entries: [
          {
            id: 5,
            player_name: "سارة",
            difficulty: "easy",
            attempts: 6,
            duration_seconds: 45,
            finished_at: "2026-11-26T00:00:00Z",
            rank: 1,
          },
        ],
      },
    });
    render(<App />);

    const table = await screen.findByRole("table");
    expect(within(table).getByText("سارة")).toBeInTheDocument();
    expect(within(table).getByText("00:45")).toBeInTheDocument();
  });

  it("shows a retry hint when the leaderboard cannot be loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503, json: () => Promise.resolve({}) }),
    );
    vi.spyOn(console, "error").mockImplementation(() => {});

    render(<App />);

    expect(await screen.findByText(/تعذّر تحميل لوحة الصدارة/)).toBeInTheDocument();
  });
});
