"use client";

import { useState } from "react";

export default function Home() {
  const [message, setMessage] = useState("Click to test the backend.");

  async function checkBackend() {
    setMessage("Checking…");

    try {
      const response = await fetch("/api/health");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setMessage(`FastAPI status: ${data.status}`);
    } catch {
      setMessage("Could not reach FastAPI.");
    }
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">Instagram Project</h1>
      <button type="button" onClick={checkBackend}>
        Check backend
      </button>
      <p aria-live="polite">{message}</p>
    </main>
  );
}
