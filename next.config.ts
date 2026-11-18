import type { NextConfig } from "next";

const isDevelopment = process.env.NODE_ENV === "development";

const csp = [
  "default-src 'self'",
  `script-src 'self' ${isDevelopment ? "'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://res.cloudinary.com",
  "font-src 'self'",
  `connect-src 'self' ${isDevelopment ?? "http://127.0.0.1:8000 http://localhost:8000 ws://localhost:3000"}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  experimental: {
    agentFeedback: true,
  },
  allowedDevOrigins: ["192.168.0.14"],

  async rewrites() {
    const backendUrl = process.env.FASTAPI_URL ?? "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
        headers: [
          {
            key: "Content-Security-Policy-Report-Only",
            value: csp,
          },
        ],
      },
    ];
  },
};

export default nextConfig;
