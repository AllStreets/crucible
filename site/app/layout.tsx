import type { Metadata } from "next";
import "./globals.css";
import { Masthead } from "../components/Masthead";
import { Colophon } from "../components/Colophon";
import { CommandPalette } from "../components/CommandPalette";
import { loadDataset, searchIndex } from "../lib/dataset";

export const metadata: Metadata = {
  title: "CRUCIBLE",
  description:
    "What actually happens when agents share a machine. Measured, not estimated.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const index = searchIndex(loadDataset());
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
        />
      </head>
      <body>
        <Masthead />
        <main>{children}</main>
        <Colophon />
        <CommandPalette items={index} />
      </body>
    </html>
  );
}
