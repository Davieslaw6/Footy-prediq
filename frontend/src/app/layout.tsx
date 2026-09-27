import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "Football Predictions",
  description: "AI-powered football match predictions",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <header className="border-b border-white/10 bg-[#080a10] px-4 py-3 text-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
            <Link href="/" className="font-semibold">Football Predictor</Link>
            <Link
              href="/training"
              className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-black transition hover:opacity-90"
            >
              Import CSV & Train
            </Link>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
