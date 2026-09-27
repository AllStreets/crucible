"use client";

import { useEffect, useState } from "react";

/** The section index that stays with the reader. Active state follows the
 *  scroll; the list itself is passed in by the page from the sections it
 *  actually rendered, so it cannot name a section that is not there. */
export function Rail({ items }: { items: { id: string; label: string }[] }) {
  const [active, setActive] = useState(items[0]?.id);
  useEffect(() => {
    const obs = new IntersectionObserver((entries) => {
      const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (vis[0]) setActive(vis[0].target.id);
    }, { rootMargin: "-20% 0px -65% 0px", threshold: 0 });
    for (const it of items) { const el = document.getElementById(it.id); if (el) obs.observe(el); }
    return () => obs.disconnect();
  }, [items]);
  return (
    <nav className="rail" aria-label="on this page">
      {items.map((it) => (
        <a key={it.id} href={`#${it.id}`} className={it.id === active ? "on" : ""}>
          <span className="tick" /><span>{it.label}</span>
        </a>
      ))}
    </nav>
  );
}
