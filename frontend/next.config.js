/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produces a minimal .next/standalone server bundle for a lean Docker
  // image (see frontend/Dockerfile) — no effect on `next dev`.
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
    ],
  },
};

module.exports = nextConfig;
