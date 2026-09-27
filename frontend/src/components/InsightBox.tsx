export function InsightBox({ text }: { text: string }) {
  return (
    <div className="mt-3 rounded-lg border border-sky-500/20 bg-sky-500/[0.07] px-3.5 py-2.5">
      <p className="text-sm leading-relaxed text-sky-200">{text}</p>
    </div>
  );
}
