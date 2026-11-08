import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Home from "../page";

describe("Home page backend check", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("renders the page and displays the backend health response", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok" }),
    });

    render(<Home />);

    expect(screen.getByRole("heading", { name: "Instagram Project" })).toBeDefined();
    expect(screen.getByText("Click to test the backend.")).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: "Check backend" }));

    expect(await screen.findByText("FastAPI status: ok")).toBeDefined();
    expect(fetchMock).toHaveBeenCalledWith("/api/health");
  });

  it("shows an error message when the backend request fails", async () => {
    fetchMock.mockRejectedValue(new Error("Network error"));

    render(<Home />);
    fireEvent.click(screen.getByRole("button", { name: "Check backend" }));

    expect(await screen.findByText("Could not reach FastAPI.")).toBeDefined();
  });
});
