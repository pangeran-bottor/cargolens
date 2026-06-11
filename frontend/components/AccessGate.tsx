"use client";

import { useEffect, useState } from "react";

import { getAccessCode, saveAccessCode, verifyAccessCode } from "@/lib/api";

/** One-time unlock screen. The code is verified against the API and kept in
 *  localStorage; when the backend has no ACCESS_CODE set (local dev), any
 *  first request succeeds and the gate never shows. */
export default function AccessGate({ children }: { children: React.ReactNode }) {
  // null = still checking the saved code, false = locked, true = unlocked
  const [unlocked, setUnlocked] = useState<boolean | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    verifyAccessCode(getAccessCode())
      .then(setUnlocked)
      .catch(() => setUnlocked(false));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (await verifyAccessCode(code.trim())) {
        saveAccessCode(code.trim());
        setUnlocked(true);
      } else {
        setError("That code wasn't accepted. Please check it and try again.");
      }
    } catch {
      setError("Could not reach the API. Please try again shortly.");
    } finally {
      setBusy(false);
    }
  }

  if (unlocked) return <>{children}</>;

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-bold text-slate-900">CargoLens</h1>
        <p className="mt-1 text-sm text-slate-500">
          This demo is access-protected. Enter the access code provided with
          the submission.
        </p>
        {unlocked === null ? (
          <p className="mt-4 text-sm text-slate-400">Checking access…</p>
        ) : (
          <form onSubmit={submit} className="mt-4 space-y-3">
            <input
              type="password"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Access code"
              autoFocus
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-400"
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={busy || !code.trim()}
              className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            >
              {busy ? "Checking…" : "Enter"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
