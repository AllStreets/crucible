"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { Billboard, Edges, OrbitControls, Text } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import type { Lattice, LatticeCell } from "../../lib/dataset";
import { token, useThemeVersion } from "../../lib/theme";

/** The arena as a solid: attackers along one axis, victims along the other,
 *  scenarios stacked in the third.
 *
 *  This is three-dimensional because the data is. A pair is not symmetric:
 *  one agent writes into the shared workspace and the other reads it, and a
 *  pair that holds one way round has not been shown to hold the other. The
 *  flat matrix collapses those two facts into one cell and hides the question.
 *  Here they are separate axes, so a row that is full and a column that is
 *  empty are different shapes, and an empty column reads as what it is:
 *  nothing tested, which is not the same as an attack that failed.
 *
 *  Everything about the camera is deliberate and dull. It does not spin on its
 *  own, it cannot fall below the floor or tip over the top, the wheel is left
 *  to the page so scrolling past never traps the reader, and the four named
 *  viewpoints are the ones worth looking from. A figure that drifts while you
 *  are reading it is a figure you cannot point at.
 */

/** The figure's colours, read from the theme tokens so the solid follows the light and
 *  dark themes. three.js needs concrete values, so these are resolved in the browser and
 *  re-read when the theme changes; the defaults are the dark theme, for the first render. */
interface Palette { fail: string; done: string; artifact: string; blocked: string; lost: string;
  ink: string; label: string; outline: string; floor: string; floorEdge: string }
const DARK: Palette = { fail: "#E4632A", done: "#34A48F", artifact: "#8B72C6", blocked: "#4B4B52", lost: "#4B4B52",
  ink: "#ECEAE4", label: "#C9C5BC", outline: "#0B0B0D", floor: "#17171C", floorEdge: "#232327" };
function readPalette(): Palette {
  const t = (n: string, d: string) => token(n) || d;
  return { fail: t("--accent", DARK.fail), done: t("--earned", DARK.done), artifact: t("--artifact", DARK.artifact),
    blocked: t("--refused", DARK.blocked), lost: t("--refused", DARK.lost), ink: t("--ink", DARK.ink),
    label: t("--ink-over-haze", DARK.label), outline: t("--ground", DARK.outline),
    floor: t("--lattice-floor", DARK.floor), floorEdge: t("--rule", DARK.floorEdge) };
}
const TONE = DARK as unknown as Record<string, string>; // the key's swatches; the solid uses the live palette

function toneOf(c: LatticeCell): string {
  if (c.status === "done") return c.outcome === "fail" ? "fail" : "done";
  return c.status;
}

function wordFor(c: LatticeCell): string {
  const t = toneOf(c);
  if (t === "fail") return "attack confirmed";
  if (t === "done") return c.strength === "weak" ? "held, weak evidence" : "held, victim engaged";
  if (t === "artifact") return "instrument artifact";
  return "refused before the agents started";
}

const SCENARIO_LABEL: Record<string, string> = {
  induced_execution: "Induced execution",
  partner_escalation: "Partner escalation",
  secret_exfiltration: "Secret exfiltration",
  state_poisoning: "State poisoning",
};

/** Short enough to read on an axis, taken from the slug rather than invented. */
function shortName(slug: string, names: Record<string, string>): string {
  return names[slug] ?? slug;
}

const GAP = 1.5;
const LAYER = 2.1;

type View = "default" | "attacker" | "victim" | "scenario";

const VIEW_LABEL: Record<View, { label: string; hint: string }> = {
  default: { label: "Corner", hint: "all three axes at once" },
  attacker: { label: "Down the attackers", hint: "who induces" },
  victim: { label: "Down the victims", hint: "who complies" },
  scenario: { label: "From above", hint: "one scenario per layer" },
};

/** Camera positions are computed from the size of the solid rather than
 *  written down, so the figure still frames itself when an agent or a
 *  scenario is added and nobody has to come back and re-tune a number. */
function viewpoints(agents: number, layers: number) {
  const span = Math.max(4, agents * GAP);
  const lift = Math.max(2.5, layers * LAYER);
  return {
    default: [span * 1.45, lift * 0.95 + span * 0.3, span * 1.75],
    attacker: [span * 2.6, lift * 0.7, 0.01],
    victim: [0.01, lift * 0.7, span * 2.6],
    scenario: [0.01, span * 2.4 + lift, 0.01],
  } as Record<View, [number, number, number]>;
}

function Cell({ cell, x, y, z, dim, onPick, onSelect, picked, selected, pal }: {
  cell: LatticeCell; x: number; y: number; z: number; dim: boolean; pal: Palette;
  onPick: (c: LatticeCell | null) => void; onSelect: (c: LatticeCell) => void;
  picked: boolean; selected: boolean;
}) {
  const tone = toneOf(cell);
  const colour = (pal as unknown as Record<string, string>)[tone] ?? pal.blocked;
  const confirmed = tone === "fail";
  // A confirmed attack is the thing a reader is looking for, so it is the
  // only cell allowed to be solid and full height. Everything else is a
  // flatter tile, which keeps the stack readable from the side.
  const h = confirmed ? 0.9 : tone === "done" ? 0.44 : 0.2;
  const ref = useRef<import("three").Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current || !confirmed) return;
    // The one moving thing on the figure, and only on the finding itself.
    const t = 0.5 + 0.5 * Math.sin(clock.elapsedTime * 1.6);
    (ref.current.material as import("three").MeshStandardMaterial).emissiveIntensity = 0.35 + t * 0.5;
  });
  return (
    <mesh
      ref={ref}
      position={[x, y + h / 2, z]}
      onPointerOver={(e: ThreeEvent<PointerEvent>) => { e.stopPropagation(); onPick(cell); }}
      onPointerOut={() => onPick(null)}
      onClick={(e: ThreeEvent<MouseEvent>) => { e.stopPropagation(); onSelect(cell); }}
    >
      <boxGeometry args={[1.02, h, 1.02]} />
      <meshStandardMaterial
        color={colour}
        emissive={colour}
        emissiveIntensity={confirmed ? 0.5 : 0.12}
        transparent
        opacity={dim ? 0.1 : 1}
        roughness={0.45}
        metalness={0.1}
      />
      {(picked || selected || confirmed) && (
        <Edges color={selected ? pal.fail : picked ? pal.ink : colour} />
      )}
    </mesh>
  );
}

function AxisLabel({ text, position, rotation, anchorX, color, pal }: {
  text: string; position: [number, number, number];
  rotation?: [number, number, number]; anchorX?: "left" | "right" | "center";
  color?: string; pal: Palette;
}) {
  return (
    <Text
      position={position}
      rotation={rotation}
      fontSize={0.5}
      color={color ?? pal.label}
      anchorX={anchorX ?? "center"}
      anchorY="middle"
      outlineWidth={0.012}
      outlineColor={pal.outline}
      /* A label that the thing it labels can hide is not a label. These draw
         over the solid rather than inside it. */
      renderOrder={999}
      material-depthTest={false}
      material-transparent
    >
      {text}
    </Text>
  );
}

function Scene({ data, names, view, focus, onPick, onSelect, picked, selected, pal }: {
  data: Lattice; names: Record<string, string>; view: View; focus: string | null; pal: Palette;
  onPick: (c: LatticeCell | null) => void; onSelect: (c: LatticeCell) => void;
  picked: LatticeCell | null; selected: LatticeCell | null;
}) {
  const controls = useRef<OrbitControlsImpl>(null);
  const n = data.agents.length;
  const half = ((n - 1) * GAP) / 2;
  const at = (i: number) => i * GAP - half;
  const views = useMemo(() => viewpoints(n, data.scenarios.length), [n, data.scenarios.length]);

  useFrame(({ camera }) => {
    const want = views[view];
    // Eased, not snapped, so the reader keeps their bearings between views.
    camera.position.lerp({ x: want[0], y: want[1], z: want[2] } as import("three").Vector3, 0.08);
    controls.current?.update();
  });

  return (
    <>
      <ambientLight intensity={0.75} />
      <directionalLight position={[8, 14, 6]} intensity={1.1} />
      <directionalLight position={[-8, 4, -6]} intensity={0.35} color={pal.fail} />

      {data.scenarios.map((s, si) => {
        const y = si * LAYER;
        const hot = data.cells.some((c) => c.scenario === s && toneOf(c) === "fail");
        return (
          <group key={s}>
            {/* The floor of each layer, so an empty cell reads as empty rather
                than as absent. */}
            <mesh position={[0, y - 0.04, 0]} rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[(n - 0.1) * GAP, (n - 0.1) * GAP]} />
              <meshBasicMaterial color={pal.floor} transparent opacity={0.34} />
              <Edges color={pal.floorEdge} />
            </mesh>
            {/* Front-left of the solid rather than behind it. Depth tricks
                did not survive the text renderer, and a position the solid
                cannot stand in front of needs none. */}
            <Billboard position={[-half - 2.1, y + 0.5, half + 0.6]}>
              <AxisLabel text={SCENARIO_LABEL[s] ?? s} position={[0, 0, 0]} anchorX="right"
                         color={hot ? pal.fail : undefined} pal={pal} />
            </Billboard>
          </group>
        );
      })}

      {data.cells.map((c) => {
        const ai = data.agents.indexOf(c.attacker);
        const vi = data.agents.indexOf(c.victim);
        const si = data.scenarios.indexOf(c.scenario);
        if (ai < 0 || vi < 0 || si < 0) return null;
        const dim = focus !== null && c.attacker !== focus && c.victim !== focus;
        return (
          <Cell
            key={`${c.attacker}|${c.victim}|${c.scenario}`}
            cell={c} x={at(ai)} y={si * LAYER} z={at(vi)} dim={dim}
            onPick={onPick} onSelect={onSelect} pal={pal}
            picked={picked?.attacker === c.attacker && picked?.victim === c.victim
              && picked?.scenario === c.scenario}
            selected={selected?.attacker === c.attacker && selected?.victim === c.victim
              && selected?.scenario === c.scenario}
          />
        );
      })}

      {/* Which end of each axis is which. The names themselves live in HTML
          beside the figure: text laid on a floor is unreadable from any angle
          that also shows the solid, and a label a reader has to tilt their
          head for is not a label. */}
      <AxisLabel text="attacker →" position={[0, -1.3, half + 1.6]} rotation={[-Math.PI / 2, 0, 0]} pal={pal} />
      <AxisLabel text="victim →" position={[half + 1.6, -1.3, 0]} rotation={[-Math.PI / 2, 0, -Math.PI / 2]} pal={pal} />

      <OrbitControls
        ref={controls}
        makeDefault
        target={[0, ((data.scenarios.length - 1) * LAYER) / 2, 0]}
        enablePan={false}
        /* The wheel belongs to the page. A figure that swallows it traps the
           reader halfway down the document, which is the single most common
           way a three-dimensional figure on a page goes wrong. */
        enableZoom={false}
        autoRotate={false}
        enableDamping
        dampingFactor={0.12}
        rotateSpeed={0.55}
        /* It cannot be tipped under the floor or over the top, because neither
           view means anything and both lose the reader. */
        minPolarAngle={0.35}
        maxPolarAngle={Math.PI / 2.05}
      />
    </>
  );
}

export function ArenaLattice({ data, names }: { data: Lattice; names: Record<string, string> }) {
  const [view, setView] = useState<View>("default");
  const [picked, setPicked] = useState<LatticeCell | null>(null);
  // Clicking a block holds it, because hovering could not survive the journey
  // to the link it offers: the readout vanished the moment the pointer left
  // the block, so the one useful thing in it was unreachable.
  const [selected, setSelected] = useState<LatticeCell | null>(null);
  const [focus, setFocus] = useState<string | null>(null);
  const shown = selected ?? picked;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setSelected(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const confirmed = useMemo(() => data.cells.filter((c) => toneOf(c) === "fail"), [data.cells]);
  const themeVersion = useThemeVersion();
  const [pal, setPal] = useState<Palette>(DARK);
  useEffect(() => { setPal(readPalette()); }, [themeVersion]);

  if (data.agents.length < 2) return null;

  return (
    <div className="lattice">
      <div className="lattice-head">
        <div className="views" role="group" aria-label="viewpoint">
          {(Object.keys(VIEW_LABEL) as View[]).map((v) => (
            <button
              key={v}
              type="button"
              className={v === view ? "on" : ""}
              onClick={() => setView(v)}
              title={VIEW_LABEL[v].hint}
            >
              {VIEW_LABEL[v].label}
            </button>
          ))}
        </div>
        <label className="focus">
          <span>Isolate</span>
          <select value={focus ?? ""} onChange={(e) => setFocus(e.target.value || null)}>
            <option value="">every agent</option>
            {data.agents.map((a) => <option key={a} value={a}>{shortName(a, names)}</option>)}
          </select>
        </label>
      </div>

      <div className="stage" role="img"
           aria-label={`A 3D grid of ${data.cells.length} ordered pairings: attackers on one axis, victims on the other, ${data.scenarios.length} scenarios stacked. Each block shows that pairing's newest run; in ${confirmed.length} of them it confirmed an attack. The same data is in the table below the figure.`}>
        <Canvas camera={{ position: viewpoints(data.agents.length, data.scenarios.length).default, fov: 40 }}
                dpr={[1, 2]} onPointerMissed={() => setSelected(null)}>
          <Scene data={data} names={names} view={view} focus={focus} pal={pal}
                 onPick={setPicked} onSelect={setSelected}
                 picked={picked} selected={selected} />
        </Canvas>

        <div className={`readout${selected ? " held" : ""}`} aria-live="polite">
          {shown ? (
            <>
              <span className="pair">
                <b>{shortName(shown.attacker, names)}</b> attacking{" "}
                <b>{shortName(shown.victim, names)}</b>
              </span>
              <span className="what">{SCENARIO_LABEL[shown.scenario] ?? shown.scenario}</span>
              <span className={`state ${toneOf(shown)}`}>{wordFor(shown)}</span>
              {selected ? (
                <span className="links">
                  <Link href={`/pairs/${shown.pairKey}/#${shown.scenario}`}>open the run</Link>
                  <button type="button" onClick={() => setSelected(null)}>release</button>
                </span>
              ) : (
                <span className="hintline">click to hold this open</span>
              )}
            </>
          ) : (
            <span className="idle">
              Point at any block to read it, and click to hold it open so you can follow it
              through. Drag to turn the solid; the four viewpoints above are the ones worth
              looking from.
            </span>
          )}
        </div>
      </div>

      <div className="axes">
        <div>
          <span className="label">attacker axis</span>
          <ol>{data.agents.map((a) => <li key={a}>{shortName(a, names)}</li>)}</ol>
        </div>
        <div>
          <span className="label">victim axis</span>
          <ol>{data.agents.map((a) => <li key={a}>{shortName(a, names)}</li>)}</ol>
        </div>
      </div>

      <ul className="key">
        <li><i style={{ background: TONE.fail }} />attack confirmed</li>
        <li><i style={{ background: TONE.done }} />held</li>
        <li><i style={{ background: TONE.artifact }} />instrument artifact</li>
        <li><i style={{ background: TONE.blocked }} />refused</li>
        <li><i className="empty" />never run in this direction</li>
      </ul>

      {/* the solid's text alternative: every block, readable without a pointer or a GPU */}
      <details className="as-table">
        <summary>Read this figure as a table ({data.cells.length} pairings)</summary>
        <div className="as-table-scroll">
          <table>
            <thead><tr><th scope="col">Attacker</th><th scope="col">Victim</th><th scope="col">Scenario</th><th scope="col">Newest result</th><th scope="col">Runs</th></tr></thead>
            <tbody>
              {[...data.cells]
                .sort((a, b) => (toneOf(a) === "fail" ? 0 : 1) - (toneOf(b) === "fail" ? 0 : 1)
                  || a.attacker.localeCompare(b.attacker) || a.victim.localeCompare(b.victim) || a.scenario.localeCompare(b.scenario))
                .map((c) => (
                  <tr key={`${c.attacker}|${c.victim}|${c.scenario}`}>
                    <td>{shortName(c.attacker, names)}</td>
                    <td>{shortName(c.victim, names)}</td>
                    <td>{SCENARIO_LABEL[c.scenario] ?? c.scenario}</td>
                    <td><Link href={`/pairs/${c.pairKey}/#${c.scenario}`} className={`state ${toneOf(c)}`}>{wordFor(c)}</Link></td>
                    <td className="mono">{c.runs}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </details>

      <p className="note">
        {confirmed.length > 0 && (
          <>Every confirmed attack sits in one layer, and the blocks below it are
          the same pairs holding under the other scenarios. </>
        )}
        The solid is read as a volume: a full row is an agent that has attacked
        everything, a full column is one that has defended against everything,
        and a gap is a direction nobody has run yet rather than an attack that
        failed.
      </p>

      <style>{`
        .lattice { display: flex; flex-direction: column; gap: 1rem; min-width: 0; }
        .lattice-head { display: flex; flex-wrap: wrap; gap: 1rem 1.5rem; align-items: center;
          justify-content: space-between; }
        .views { display: flex; flex-wrap: wrap; gap: 0.4rem; }
        .views button { font-family: var(--font-body); font-size: var(--t-small); color: var(--ink-soft);
          background: transparent; border: var(--hair) solid var(--rule); padding: 0.4rem 0.8rem;
          cursor: pointer; border-radius: 2px; transition: color 140ms, border-color 140ms; }
        .views button:hover { color: var(--ink); border-color: var(--rule-strong); }
        .views button.on { color: var(--ground); background: var(--ink); border-color: var(--ink); }
        .focus { display: inline-flex; align-items: center; gap: 0.6rem; font-size: var(--t-small);
          color: var(--ink-soft); }
        .focus select { font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink);
          background: var(--panel); border: var(--hair) solid var(--rule); padding: 0.35rem 0.5rem; }

        .stage { position: relative; height: clamp(420px, 56vh, 620px); border: var(--hair) solid var(--rule);
          background: radial-gradient(120% 90% at 50% 10%, var(--lattice-top) 0%, var(--ground) 70%); }
        .stage canvas { display: block; touch-action: pan-y; }

        .readout { position: absolute; left: 0; right: 0; bottom: 0; display: flex; flex-wrap: wrap;
          gap: 0.5rem 1.4rem; align-items: baseline; padding: 0.85rem 1rem;
          background: color-mix(in srgb, var(--ground) 86%, transparent);
          border-top: var(--hair) solid var(--rule); font-size: var(--t-small); }
        .readout .pair b { font-weight: 400; font-family: var(--font-mono); color: var(--ink); }
        .readout .pair { color: var(--ink-soft); }
        .readout .what { font-family: var(--font-display); font-style: italic; font-size: var(--t-lead);
          color: var(--ink); }
        .readout .idle { color: var(--ink-faint); max-width: 62ch; }
        .readout.held { border-top-color: var(--accent); }
        .readout .links { margin-left: auto; display: flex; gap: 1.2rem; align-items: baseline; }
        .readout .links button { background: transparent; border: 0; padding: 0; cursor: pointer;
          font-family: var(--font-body); font-size: var(--t-small); color: var(--ink-faint);
          text-decoration: underline; text-underline-offset: 0.18em; }
        .readout .links button:hover { color: var(--ink); }
        .readout .hintline { margin-left: auto; font-size: var(--t-small); color: var(--ink-faint); }

        .axes { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
          gap: 1rem 2.5rem; border-top: var(--hair) solid var(--rule); padding-top: 0.9rem; }
        .axes ol { list-style: none; margin: 0.45rem 0 0; padding: 0; display: flex; flex-wrap: wrap;
          gap: 0.3rem 0.9rem; font-family: var(--font-mono); font-size: var(--t-small);
          color: var(--ink-soft); counter-reset: ax; }
        .axes li { counter-increment: ax; }
        .axes li::before { content: counter(ax) " "; color: var(--ink-faint); }

        .key { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap;
          gap: 0.5rem 1.5rem; font-size: var(--t-small); color: var(--ink-soft); }
        .key li { display: flex; align-items: center; gap: 0.5rem; }
        .key i { width: 16px; height: 10px; border-radius: 1px; display: inline-block; }
        .key i.empty { background: transparent; box-shadow: inset 0 0 0 1px var(--rule-strong); }

        .lattice .note { font-size: var(--t-small); color: var(--ink-soft); max-width: var(--measure); }
        .as-table summary { cursor: pointer; font-size: var(--t-small); color: var(--ink-soft); }
        .as-table summary:focus-visible { outline: 1px solid var(--accent); outline-offset: 3px; }
        .as-table-scroll { overflow-x: auto; margin-top: 0.75rem; max-height: 28rem; overflow-y: auto; border: var(--hair) solid var(--rule); }
        .as-table table { width: 100%; border-collapse: collapse; font-size: var(--t-small); }
        .as-table th, .as-table td { text-align: left; padding: 0.4rem 0.75rem; border-bottom: var(--hair) solid var(--rule); white-space: nowrap; }
        .as-table th { position: sticky; top: 0; background: var(--ground-raised); color: var(--ink-faint); font-weight: 500; }
        .as-table td a { text-decoration: none; }

        @media (max-width: 720px) {
          .stage { height: 380px; }
          .readout .links, .readout .hintline { margin-left: 0; }
        }
      `}</style>
    </div>
  );
}
