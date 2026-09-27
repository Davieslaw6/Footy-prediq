import { notFound } from "next/navigation";
import { MatchHeader } from "@/components/MatchHeader";
import { PredictionCard } from "@/components/PredictionCard";
import type { MatchPrediction } from "@/types/prediction";

const PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const SERVER_API_BASE = process.env.INTERNAL_API_BASE ?? PUBLIC_API_BASE;

type PredictionResult =
  | { kind: "ok"; data: MatchPrediction }
  | { kind: "not_found" }
  | { kind: "not_ready"; detail: string }
  | { kind: "error"; detail: string };

async function getPrediction(matchId: string): Promise<PredictionResult> {
  let res: Response;
  try {
    res = await fetch(`${SERVER_API_BASE}/api/predictions/${matchId}`, { cache: "no-store" });
  } catch {
    return { kind: "error", detail: "Could not reach the prediction service. Please try again shortly." };
  }

  if (res.status === 404) return { kind: "not_found" };

  if (!res.ok) {
    let detail = `Failed to load prediction (${res.status}).`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
    }
    return res.status === 503 ? { kind: "not_ready", detail } : { kind: "error", detail };
  }

  return { kind: "ok", data: await res.json() };
}

function StatusMessage({ text }: { text: string }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#080a10] px-4 py-8">
      <div className="max-w-sm rounded-2xl border border-white/[0.08] bg-[#12151f] p-6 text-center text-sm text-slate-300">
        {text}
      </div>
    </main>
  );
}

export default async function MatchPredictionPage({ params }: { params: { id: string } }) {
  const result = await getPrediction(params.id);

  if (result.kind === "not_found") notFound();
  if (result.kind === "not_ready") return <StatusMessage text={result.detail} />;
  if (result.kind === "error") return <StatusMessage text={result.detail} />;

  const data = result.data;

  return (
    <main className="min-h-screen bg-[#080a10] px-4 py-8">
      <div className="mx-auto flex max-w-md flex-col gap-4">
        <MatchHeader
          homeTeam={data.home_team}
          awayTeam={data.away_team}
          kickoffUtc={data.kickoff_utc}
          league={data.league}
        />

        <PredictionCard
          title="Winner"
          confidence={data.winner.confidence}
          risk={data.winner.risk}
          call={data.winner.call}
          insight={data.winner.insight}
        />

        <PredictionCard
          title="Over/Under"
          confidence={data.over_under.confidence}
          risk={data.over_under.risk}
          call={data.over_under.call}
          insight={data.over_under.insight}
        />

        <PredictionCard
          title="Corners"
          confidence={data.corners.confidence}
          risk={data.corners.risk}
          call={data.corners.call}
          insight={data.corners.insight}
        />
      </div>
    </main>
  );
}
