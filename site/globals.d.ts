// TypeScript 6 does not pick up Next's ambient CSS declaration through
// next-env.d.ts, so the side-effect import of a stylesheet needs one here.
declare module "*.css";
