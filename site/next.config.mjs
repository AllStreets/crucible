/** @type {import('next').NextConfig} */
const nextConfig = {
  // Fully static. The site reads three JSON files at build time and has no
  // runtime data source, so there is nothing for a server to do. This is not
  // an optimisation, it is the structural guarantee: a static export cannot
  // acquire a database connection later without someone noticing.
  output: "export",
  // This directory is the workspace root. Without it Next walks up and finds a
  // lockfile in the home directory, then traces files from there.
  outputFileTracingRoot: import.meta.dirname,
  reactStrictMode: true,
  // Emit out/<route>/index.html rather than out/<route>.html, so a directory
  // URL resolves on any static host without rewrite rules.
  trailingSlash: true,
};
export default nextConfig;
