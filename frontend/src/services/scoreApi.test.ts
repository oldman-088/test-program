import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchLeaderboard, submitScore } from "./scoreApi";

function mockFetch(body: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("submitScore", () => {
  it("posts the payload as JSON", async () => {
    const created = {
      id: 7,
      player_name: "ليلى",
      difficulty: "easy",
      attempts: 10,
      duration_seconds: 42,
      finished_at: "2026-11-26T00:00:00Z",
      rank: 1,
    };
    const fetchMock = mockFetch(created, 201);

    const result = await submitScore({
      player_name: "ليلى",
      difficulty: "easy",
      attempts: 10,
      duration_seconds: 42,
    });

    expect(result).toEqual(created);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/scores",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          player_name: "ليلى",
          difficulty: "easy",
          attempts: 10,
          duration_seconds: 42,
        }),
      }),
    );
  });

  it("throws on a 422 response", async () => {
    mockFetch({ detail: [] }, 422);
    await expect(
      submitScore({
        player_name: "",
        difficulty: "easy",
        attempts: 1,
        duration_seconds: 1,
      }),
    ).rejects.toMatchObject({ status: 422 });
  });
});

describe("fetchLeaderboard", () => {
  it("builds the query string and returns the board", async () => {
    const board = { difficulty: "hard", limit: 5, total: 0, entries: [] };
    const fetchMock = mockFetch(board);

    const result = await fetchLeaderboard("hard", 5);

    expect(result).toEqual(board);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/leaderboard?difficulty=hard&limit=5");
  });

  it("surfaces network errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(fetchLeaderboard("easy")).rejects.toThrow("Failed to fetch");
  });
});
