export function Prose({ children }: { children: React.ReactNode }) {
  return (
    <div className="prose">
      {children}
      <style>{`
        .prose { display: flex; flex-direction: column; gap: 1.1rem; max-width: 68ch; }
        .prose p { font-size: var(--t-lead); line-height: 1.55; color: var(--ink); }
        .prose h3 { margin-top: 1.6rem; font-style: italic; }
        .prose ul { margin: 0; padding-left: 1.1rem; max-width: var(--measure); }
        .prose li { margin-bottom: 0.5rem; }
      `}</style>
    </div>
  );
}

/** A numbered figure with a hairline rule, referenced by number in the prose.
 *  Journal convention, used because these pages are read the way a method
 *  section is read: to decide whether to trust anything else on the site. */
export function Figure(
  { n, caption, children }: { n: number; caption: string; children: React.ReactNode },
) {
  return (
    <figure className="fig">
      <div className="body">{children}</div>
      <figcaption>
        <span className="label">Figure {n}</span>
        <span>{caption}</span>
      </figcaption>
      <style>{`
        .fig { margin: 1.75rem 0; }
        .fig .body {
          border-top: var(--rule-hair) solid var(--ink);
          border-bottom: var(--rule-hair) solid var(--rule);
          padding: 1.1rem 0;
        }
        .fig figcaption {
          display: flex;
          gap: 0.9rem;
          align-items: baseline;
          padding-top: 0.6rem;
          font-size: var(--t-small);
          color: var(--ink-soft);
          max-width: var(--measure);
        }
        .fig figcaption .label { white-space: nowrap; }
      `}</style>
    </figure>
  );
}
