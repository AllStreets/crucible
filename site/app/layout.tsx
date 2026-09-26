import type { Metadata } from "next";
import "./globals.css";
import { Masthead } from "../components/Masthead";
import { Colophon } from "../components/Colophon";

export const metadata: Metadata = {
  title: "CRUCIBLE",
  description:
    "What actually happens when agents share a machine. Measured, not estimated.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Public+Sans:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap"
        />
      </head>
      {/* Reading surfaces are specimen. Instrument pages set detector on their
          own body in Phase 3b. */}
      <body data-surface="specimen">
        <Masthead />
        <main>{children}</main>
        <Colophon />
      </body>
    </html>
  );
}
