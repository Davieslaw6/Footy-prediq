import Link from "next/link";
import type { UpcomingFixture } from "@/types/prediction";

function formatKickoff(iso: string) {
  const d = new Date(iso);
  const datePart = d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  const timePart = d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${datePart}, ${timePart}`;
}

function TeamLabel({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-[10px] font-bold text-slate-300">
        {name.slice(0, 2).toUpperCase()}
      </span>
      <span className="text-sm font-medium text-slate-200">{name}</span>
    </div>
  );
}

export function FixtureList({ fixtures }: { fixtures: UpcomingFixture[] }) {
  if (fixtures.length === 0) {
    return (
      <div className="rounded-2xl border border-white/[0.08] bg-[#12151f] p-6 text-center text-sm text-slate-400">
        No upcoming fixtures yet. Import historical data and add fixtures to get started.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {fixtures.map((fixture) => (
        <Link
          key={fixture.id}
          href={`/match/${fixture.id}`}
          className="flex items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-[#12151f] p-4 shadow-lg shadow-black/20 transition hover:border-white/20"
        >
          <div className="flex flex-col gap-2">
            <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
              {fixture.league}
            </span>
            <TeamLabel name={fixture.home_team.name} />
            <TeamLabel name={fixture.away_team.name} />
          </div>
          <span className="whitespace-nowrap text-xs font-medium text-slate-400">
            {formatKickoff(fixture.kickoff_utc)}
          </span>
        </Link>
      ))}
    </div>
  );
}
