import Image from "next/image";
import type { TeamInfo } from "@/types/prediction";

function formatMatchDate(iso: string) {
  const d = new Date(iso);
  const datePart = d.toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const timePart = d.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return { datePart, timePart };
}

function TeamCrest({ team }: { team: TeamInfo }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex h-14 w-14 items-center justify-center rounded-full border border-white/10 bg-white/[0.04]">
        {team.logo_url ? (
          <Image src={team.logo_url} alt={team.name} width={40} height={40} className="rounded-full" />
        ) : (
          <span className="text-lg font-bold text-slate-300">{team.name.slice(0, 2).toUpperCase()}</span>
        )}
      </div>
      <span className="max-w-[110px] text-center text-sm font-medium text-slate-200">{team.name}</span>
    </div>
  );
}

export function MatchHeader({
  homeTeam,
  awayTeam,
  kickoffUtc,
  league,
}: {
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  kickoffUtc: string;
  league: string;
}) {
  const { datePart, timePart } = formatMatchDate(kickoffUtc);

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#0d0f17] p-6">
      <p className="text-center text-xs font-medium uppercase tracking-wide text-slate-500">{league}</p>
      <div className="mt-4 flex items-center justify-between px-2">
        <TeamCrest team={homeTeam} />
        <div className="flex flex-col items-center gap-1">
          <span className="text-2xl font-bold text-slate-600">VS</span>
          <span className="text-lg font-semibold text-slate-100">{timePart}</span>
        </div>
        <TeamCrest team={awayTeam} />
      </div>
      <p className="mt-5 text-center text-sm text-slate-400">{datePart}</p>
    </div>
  );
}
