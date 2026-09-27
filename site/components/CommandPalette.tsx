"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { SearchItem } from "../lib/dataset";

/** Cmd+K over a build-time index of pages, agents, scenarios and pairs.
 *
 *  Retrieval only. Everything with a row is reachable by name, and no model
 *  is consulted: a palette that answers from the index costs nothing and
 *  cannot say anything the index does not contain. Bound to K, not Q, since
 *  Cmd+Q quits the browser. */
export function CommandPalette({ items }: { items: SearchItem[] }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); }
      if (e.key === "Escape") setOpen(false);
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("crucible:palette", onOpen);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("crucible:palette", onOpen); };
  }, []);

  useEffect(() => { if (open) { setQ(""); setActive(0); setTimeout(() => input.current?.focus(), 10); } }, [open]);

  const results = useMemo(() => {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    const score = (it: SearchItem) => {
      const t = it.title.toLowerCase(), h = it.hint.toLowerCase(), k = it.kind;
      if (!terms.every((w) => t.includes(w) || h.includes(w) || k.includes(w))) return -1;
      let s = 0;
      for (const w of terms) { if (t.startsWith(w)) s += 3; else if (t.includes(w)) s += 2; else s += 1; }
      return s;
    };
    return items.map((it) => [score(it), it] as const).filter(([s]) => s >= 0)
      .sort((a, b) => b[0] - a[0]).slice(0, 12).map(([, it]) => it);
  }, [q, items]);

  const go = (it: SearchItem) => { setOpen(false); window.location.href = it.href; };

  if (!open) return null;
  return (
    <div className="palette-backdrop" onMouseDown={() => setOpen(false)}>
      <div className="palette panel" onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label="navigate">
        <input ref={input} value={q} placeholder="Go to a page, an agent, a scenario, a pair"
          onChange={(e) => { setQ(e.target.value); setActive(0); }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)); }
            if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
            if (e.key === "Enter" && results[active]) go(results[active]);
          }} />
        <ul>
          {results.map((it, i) => (
            <li key={it.href + it.title} className={i === active ? "active" : ""}
                onMouseEnter={() => setActive(i)} onClick={() => go(it)}>
              <span className="kind">{it.kind}</span>
              <span><span>{it.title}</span><span className="hint">{it.hint}</span></span>
            </li>
          ))}
          {results.length === 0 && <li><span className="kind">none</span><span className="hint">nothing in the index matches</span></li>}
        </ul>
        <div className="foot">
          <span><span className="kbd">up</span> <span className="kbd">down</span> move</span>
          <span><span className="kbd">enter</span> open</span>
          <span><span className="kbd">esc</span> close</span>
          <span style={{ marginLeft: "auto" }}>index built from the dataset at publish time</span>
        </div>
      </div>
    </div>
  );
}
