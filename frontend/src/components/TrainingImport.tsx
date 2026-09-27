"use client";

import { useState } from "react";
import { Upload, Database, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY;

export default function TrainingImport() {
  const [file, setFile] = useState<File | null>(null);
  const [tune, setTune] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function importCsv() {
    if (!file) { setError("Select a CSV file first."); return; }
    setBusy(true); setMessage(""); setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("tune", String(tune));
      const res = await fetch(API_BASE + "/api/admin/training-data/import", {
        method: "POST",
        body: form,
        headers: ADMIN_KEY ? { "X-Admin-Key": ADMIN_KEY } : undefined,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "CSV import failed.");
      setMessage(data.detail); setFile(null);
    } catch (err) { setError(err instanceof Error ? err.message : "CSV import failed."); }
    finally { setBusy(false); }
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-[#10131b] p-5 text-white shadow-xl">
      <div className="mb-4 flex items-center gap-3">
        <div className="rounded-xl bg-white/5 p-2"><Database size={20} /></div>
        <div><h2 className="font-semibold">Train from CSV</h2><p className="text-sm text-white/50">Import historical matches and retrain the prediction models.</p></div>
      </div>
      <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-white/20 bg-white/[0.02] px-5 py-8 text-center hover:bg-white/[0.04]">
        <Upload size={24} className="mb-2 text-white/70" />
        <span className="text-sm font-medium">{file ? file.name : "Choose matches CSV"}</span>
        <span className="mt-1 text-xs text-white/40">Historical match data only</span>
        <input type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </label>
      <label className="mt-4 flex items-center gap-2 text-sm text-white/70">
        <input type="checkbox" checked={tune} onChange={(e) => setTune(e.target.checked)} />
        Tune hyperparameters with Optuna
      </label>
      <button type="button" disabled={!file || busy} onClick={importCsv} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-40">
        {busy ? <Loader2 size={17} className="animate-spin" /> : <Upload size={17} />}
        {busy ? "Importing & training..." : "Import CSV & Train"}
      </button>
      {message && <div className="mt-4 flex gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-3 text-sm text-emerald-300"><CheckCircle2 size={18} className="shrink-0" /><span>{message}</span></div>}
      {error && <div className="mt-4 flex gap-2 rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-300"><AlertCircle size={18} className="shrink-0" /><span>{error}</span></div>}
      <div className="mt-4 rounded-xl bg-white/[0.03] p-3 text-xs leading-5 text-white/45">Required columns: home_team, away_team, kickoff_utc, home_goals, away_goals, home_corners, away_corners, home_xg, away_xg, result. Result must be H, D, or A. Minimum: 50 historical matches.</div>
    </section>
  );
}