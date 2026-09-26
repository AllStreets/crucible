"use client";

import { useEffect, useRef, useState } from "react";
import type { GraphLink, GraphNode } from "../../lib/graph";

/** The interaction graph: agents, and every pair run between them.
 *
 *  Node size is degree, so an agent that has been run against many others
 *  becomes a hub without anyone deciding it should be one. Everything scales
 *  from the rows: more agents, more nodes; more runs, more edges and larger
 *  hubs. Nothing here is laid out by hand.
 */
export function InteractionGraph(
  { nodes, links }: { nodes: GraphNode[]; links: GraphLink[] },
) {
  const mount = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!mount.current) return;
    let graph: { _destructor?: () => void } | null = null;
    let cancelled = false;

    (async () => {
      try {
      const mod = await import("3d-force-graph");
      if (cancelled || !mount.current) return;
      // 3d-force-graph is a kapsule component: the import is a factory, and
      // calling it returns the initialiser that takes the DOM node. Passing the
      // element straight to the factory treats it as a config object, attaches
      // nothing, and reports no error, which is how this first shipped empty.
      const factory = (mod.default ?? mod) as unknown as () => (
        el: HTMLElement,
      ) => Record<string, (...a: unknown[]) => unknown>;

      // Degree drives size. Recomputed here rather than stored, so it stays
      // correct as runs are added without anyone updating a field.
      const degree: Record<string, number> = {};
      for (const l of links) {
        degree[l.source] = (degree[l.source] ?? 0) + 1;
        degree[l.target] = (degree[l.target] ?? 0) + 1;
      }
      const sized = nodes.map((n) => ({
        ...n,
        val: 2 + Math.log(1 + (degree[n.id] ?? 0)) * 5,
        degree: degree[n.id] ?? 0,
      }));

      const g = factory()(mount.current);
      graph = g as unknown as { _destructor?: () => void };

      const rect = mount.current.getBoundingClientRect();
      g.width(rect.width);
      g.height(rect.height);
      g.backgroundColor("rgba(0,0,0,0)");
      g.graphData({ nodes: sized, links });
      g.nodeColor((n: unknown) => (n as GraphNode).color);
      g.nodeVal((n: unknown) => (n as GraphNode).val);
      g.nodeOpacity(0.95);
      g.nodeResolution(14);
      g.linkColor((l: unknown) => (l as GraphLink).color);
      g.linkWidth((l: unknown) => (l as GraphLink).width);
      g.linkOpacity(0.55);
      g.linkCurvature((l: unknown) => (l as GraphLink).curvature);
      g.linkDirectionalParticles((l: unknown) =>
        (l as GraphLink).status === "done" ? 3 : 0);
      g.linkDirectionalParticleWidth(1.6);
      g.linkDirectionalParticleSpeed(0.006);
      // Pull unconnected agents in rather than letting repulsion fling them to
      // the edges. Most agents have no runs yet, and a layout that scatters
      // them reads as a sparser study than the one that exists.
      const charge = (g.d3Force as (n: string) => { strength: (v: number) => void } | undefined)("charge");
      charge?.strength(-85);
      const link = (g.d3Force as (n: string) => { distance: (v: number) => void } | undefined)("link");
      link?.distance(48);
      (g.d3VelocityDecay as (v: number) => void)(0.32);
      // Unconnected agents ring the core rather than drifting to the margins.
      // They belong in the picture: most agents have no runs yet, and that is
      // the finding, but a layout that flings them off-frame understates how
      // many were measured.
      const center = (g.d3Force as (n: string) => { strength: (v: number) => void } | undefined)("center");
      center?.strength(0.9);

      g.enableNodeDrag(false);
      g.showNavInfo(false);

      g.onNodeHover((n: unknown) => {
        const node = n as (GraphNode & { degree: number }) | null;
        setHover(node
          ? `${node.id}  ·  ${node.stageLabel}` +
            (node.degree ? `  ·  ${node.degree} runs` : "") +
            (node.failure ? `  ·  ${node.failure}` : "")
          : null);
      });
      g.onLinkHover((l: unknown) => {
        const link = l as GraphLink | null;
        setHover(link
          ? `${link.scenario}  ·  ${link.status}` +
            (link.outcome ? `  ·  ${link.outcome}` : "")
          : null);
      });
      g.onNodeClick((n: unknown) => {
        const url = (n as GraphNode).repoUrl;
        if (url) window.open(url, "_blank", "noopener,noreferrer");
      });

      // Fit to whatever is actually there, rather than a fixed distance that
      // would frame one dataset and lose the next. Then drift at the radius the
      // fit chose, so the framing stays right as the graph grows.
      let spin: ReturnType<typeof setInterval> | undefined;
      window.setTimeout(() => {
        (g.zoomToFit as (ms?: number, px?: number) => void)(900, 26);
        window.setTimeout(() => {
          const cam = (g.cameraPosition as () => { x: number; y: number; z: number })();
          const radius = Math.hypot(cam.x, cam.z) || 220;
          let angle = Math.atan2(cam.x, cam.z);
          spin = setInterval(() => {
            angle += Math.PI / 2200;
            (g.cameraPosition as (p: unknown) => void)({
              x: radius * Math.sin(angle), y: cam.y, z: radius * Math.cos(angle),
            });
          }, 40);
        }, 1000);
      }, 400);

      const onResize = () => {
        if (!mount.current) return;
        const r = mount.current.getBoundingClientRect();
        g.width(r.width); g.height(r.height);
      };
      window.addEventListener("resize", onResize);
      setReady(true);

      graph = {
        _destructor: () => {
          if (spin) clearInterval(spin);
          window.removeEventListener("resize", onResize);
          (g._destructor as (() => void) | undefined)?.();
        },
      };
      } catch (err) {
        // A graph that fails to mount must say so rather than leave an empty
        // frame that reads as "no interactions recorded".
        console.error("interaction graph failed to mount", err);
        setError(String(err));
      }
    })();

    return () => {
      cancelled = true;
      graph?._destructor?.();
    };
  }, [nodes, links]);

  return (
    <div className="graph3d">
      <div className="hud">
        <span className="count mono">
          {nodes.length} agents &middot; {links.length} pair runs
        </span>
        <span className="read mono">{hover ?? ""}</span>
      </div>
      <div ref={mount} className="mount" />
      {!ready && !error && <div className="boot label">initialising graph</div>}
      {error && <div className="boot err mono">graph failed to mount: {error}</div>}
      <div className="hint mono">drag rotates &middot; scroll zooms &middot; click opens the repository</div>
      <style>{`
        .graph3d { position: relative; height: clamp(380px, 48vh, 540px); }
        .mount { position: absolute; inset: 0; }
        .hud { position: absolute; inset: 0.75rem 0.75rem auto 0.75rem; z-index: 3;
               display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap;
               pointer-events: none; }
        .hud .count { font-size: var(--t-micro); letter-spacing: 0.1em;
                      text-transform: uppercase; color: var(--ink-soft);
                      background: rgba(7,8,11,0.72); padding: 0.28rem 0.55rem;
                      border: var(--hair) solid var(--rule); border-radius: 2px; }
        .hud .read { font-size: var(--t-micro); color: var(--accent);
                     background: rgba(7,8,11,0.72); padding: 0.28rem 0.55rem;
                     border-radius: 2px; max-width: 70%; overflow: hidden;
                     text-overflow: ellipsis; white-space: nowrap; }
        .hud .read:empty { display: none; }
        .boot { position: absolute; inset: 0; display: grid; place-items: center;
                color: var(--ink-faint); text-align: center; padding: 1rem; }
        .boot.err { color: var(--signal-stop); font-size: var(--t-micro); }
        .hint { position: absolute; right: 0.75rem; bottom: 0.6rem; z-index: 3;
                font-size: var(--t-micro); color: var(--ink-faint);
                background: rgba(7,8,11,0.78); padding: 0.25rem 0.5rem;
                border-radius: 2px; pointer-events: none; }
      `}</style>
    </div>
  );
}
