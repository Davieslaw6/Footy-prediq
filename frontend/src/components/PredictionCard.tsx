import { RiskBadge } from "./RiskBadge";
import { InsightBox } from "./InsightBox";
import type { RiskLevel } from "@/types/prediction";

interface PredictionCardProps {
  title: string;
  confidence: number;
  risk: RiskLevel;
  call: string;
  insight: string;
}

export function PredictionCard({ title, confidence, risk, call, insight }: PredictionCardProps) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#12151f] p-4 shadow-lg shadow-black/20">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-400">{title}:</h3>
        <div className="flex flex-col items-end gap-1.5">
          <span className="text-sm font-semibold text-slate-100">
            {confidence.toFixed(2)}%
          </span>
          <RiskBadge risk={risk} />
        </div>
      </div>

      <p className="mt-2 text-base font-medium text-slate-100">{call}</p>

      <InsightBox text={insight} />
    </div>
  );
}
