import { FixtureList } from "@/components/FixtureList";
import type { UpcomingFixture } from "@/types/prediction";

const PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const SERVER_API_BASE = process.env.INTERNAL_API_BASE ?? PUBLIC_API_BASE;

async function getUpcomingFixtures(): Promise<UpcomingFixture[]> {
  try {
    const res = await fetch(`${SERVER_API_BASE}/api/matches/upcoming`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const fixtures = await getUpcomingFixtures();

  return (
    <main className="min-h-screen bg-[#080a10] px-4 py-8">
      <div className="mx-auto flex max-w-md flex-col gap-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Upcoming Fixtures</h1>
          <p className="mt-1 text-sm text-slate-500">Tap a fixture for its match prediction.</p>
        </div>
        <FixtureList fixtures={fixtures} />
      </div>
    </main>
  );
}
