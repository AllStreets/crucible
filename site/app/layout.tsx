import type { Metadata } from "next";
import "./globals.css";
import { Masthead } from "../components/Masthead";
import { Colophon } from "../components/Colophon";
import { CommandPalette } from "../components/CommandPalette";
import { Reveal } from "../components/Reveal";
import { loadDataset, searchIndex } from "../lib/dataset";

export const metadata: Metadata = {
  title: "Crucible",
  description: "What actually happens when open-source agents share a machine. Measured, not estimated: every figure is a count of rows you can open.",
  icons: { icon: "data:image/svg+xml," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#0B0B0D"/><rect x="9" y="9" width="14" height="14" transform="rotate(45 16 16)" fill="#E4632A"/></svg>') },
  metadataBase: new URL("https://crucible-weld.vercel.app"),
  openGraph: {
    title: "Crucible",
    description: "An instrument for what happens when agents share a machine.",
    type: "website",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "Crucible's front page: \"What actually happens when agents share a machine.\" beside the record's four counts" }],
  },
  twitter: { card: "summary_large_image", title: "Crucible", description: "An instrument for what happens when agents share a machine.", images: ["/og.png"] },
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
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Instrument+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap"
        />
      </head>
      <body>
        <Masthead />
        <main>{children}</main>
        <Colophon />
        <CommandPalette items={index} />
        <Reveal />
      </body>
    </html>
  );
}
