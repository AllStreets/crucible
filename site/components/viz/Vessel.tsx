"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";

/** One specimen in the vessel: an agent, at the stage it actually reached.
 *
 *  This is not a force graph. Every agent that enters the instrument is a
 *  specimen suspended in a crucible, and its height is the stage it survived
 *  to. Agents that fell out sit cold at the bottom; the ones still reacting
 *  glow at the top. The geometry carries the finding rather than decorating it.
 */
export interface Specimen {
  slug: string;
  stage: number;        // 0 harvested, 1 built, 2 checked, 3 invocable, 4 in arena
  label: string;
  failure: string | null;
}

const STAGE_COLOR = ["#3E6E8E", "#2E9C8E", "#2E9C8E", "#C8922A", "#FF8A3D"];
// Four visible tiers. Stages 1 and 2 share a height because a built image and
// a checked environment are one rung in practice: the check does not invoke
// the agent, so it earns no extra elevation.
const STAGE_Y = [-1.5, -0.45, -0.45, 0.6, 1.6];
const STAGE_R = [2.35, 1.9, 1.9, 1.4, 0.95];
const TIERS = [
  { y: -1.5, r: 2.35, c: "#3E6E8E" },
  { y: -0.45, r: 1.9, c: "#2E9C8E" },
  { y: 0.6, r: 1.4, c: "#C8922A" },
  { y: 1.6, r: 0.95, c: "#FF8A3D" },
];

function Node({ s, index, total, onHover }: {
  s: Specimen; index: number; total: number;
  onHover: (s: Specimen | null) => void;
}) {
  const mesh = useRef<THREE.Mesh>(null);
  const angle = (index / total) * Math.PI * 2;
  const radius = STAGE_R[s.stage];
  const base = useMemo(
    () => new THREE.Vector3(Math.cos(angle) * radius, STAGE_Y[s.stage], Math.sin(angle) * radius),
    [angle, radius, s.stage],
  );
  const hot = s.stage >= 3;

  useFrame(({ clock }) => {
    if (!mesh.current) return;
    const t = clock.elapsedTime;
    // Hotter specimens are more agitated. Inert ones barely move.
    const amp = 0.015 + s.stage * 0.022;
    mesh.current.position.set(
      base.x + Math.sin(t * 0.7 + index) * amp,
      base.y + Math.sin(t * 0.9 + index * 1.7) * amp * 1.6,
      base.z + Math.cos(t * 0.6 + index) * amp,
    );
    mesh.current.rotation.y = t * (0.08 + s.stage * 0.05);
  });

  return (
    <mesh
      ref={mesh}
      onPointerOver={(e) => { e.stopPropagation(); onHover(s); }}
      onPointerOut={() => onHover(null)}
    >
      <icosahedronGeometry args={[hot ? 0.17 : 0.12, 0]} />
      <meshStandardMaterial
        color={STAGE_COLOR[s.stage]}
        emissive={STAGE_COLOR[s.stage]}
        emissiveIntensity={hot ? 1.5 : 0.35}
        roughness={0.35}
        metalness={0.6}
        flatShading
      />
    </mesh>
  );
}

/** One tier ring: the stage itself, drawn so elevation is readable structure
 *  rather than an accident of where a node happens to float. */
function Tier({ y, r, c }: { y: number; r: number; c: string }) {
  return (
    <mesh position={[0, y, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <torusGeometry args={[r, 0.006, 6, 96]} />
      <meshBasicMaterial color={c} transparent opacity={0.5} />
    </mesh>
  );
}

/** The vessel wall: a narrowing cage of vertical struts. Narrowing is the
 *  point, since fewer agents survive each stage. */
function Wall() {
  const ref = useRef<THREE.LineSegments>(null);
  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.elapsedTime * 0.03;
  });
  const geo = useMemo(() => {
    const pts: number[] = [];
    const STRUTS = 18;
    for (let i = 0; i < STRUTS; i++) {
      const a = (i / STRUTS) * Math.PI * 2;
      for (let t = 0; t < TIERS.length - 1; t++) {
        const lo = TIERS[t], hi = TIERS[t + 1];
        pts.push(Math.cos(a) * lo.r, lo.y, Math.sin(a) * lo.r);
        pts.push(Math.cos(a) * hi.r, hi.y, Math.sin(a) * hi.r);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    return g;
  }, []);
  return (
    <lineSegments ref={ref} geometry={geo}>
      <lineBasicMaterial color="#2B323F" transparent opacity={0.55} />
    </lineSegments>
  );
}

/** The molten core: heat that drives the reaction, at the base. */
function Core() {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.elapsedTime;
    const k = 1 + Math.sin(t * 1.6) * 0.06;
    ref.current.scale.setScalar(k);
    ref.current.rotation.y = t * 0.25;
    ref.current.rotation.x = t * 0.16;
  });
  return (
    <group position={[0, -2.35, 0]}>
      <mesh ref={ref}>
        <icosahedronGeometry args={[0.13, 1]} />
        <meshStandardMaterial
          color="#FF8A3D" emissive="#FF6A1F" emissiveIntensity={2.4}
          roughness={0.25} metalness={0.4} flatShading />
      </mesh>
      <pointLight intensity={22} color="#FF7A2E" distance={9} decay={2} />
    </group>
  );
}

function Scene({ specimens, onHover }: {
  specimens: Specimen[]; onHover: (s: Specimen | null) => void;
}) {
  const group = useRef<THREE.Group>(null);
  useFrame(({ clock, pointer }) => {
    if (!group.current) return;
    group.current.rotation.y = clock.elapsedTime * 0.06 + pointer.x * 0.35;
    group.current.rotation.x = 0.08 + pointer.y * 0.10;
  });
  return (
    <group ref={group}>
      <Wall />
      {TIERS.map((t) => <Tier key={t.y} {...t} />)}
      <Core />
      {specimens.map((s, i) => (
        <Node key={s.slug} s={s} index={i} total={specimens.length} onHover={onHover} />
      ))}
    </group>
  );
}

export function Vessel({ specimens }: { specimens: Specimen[] }) {
  const [hovered, setHovered] = useState<Specimen | null>(null);

  return (
    <div className="vessel">
      <Canvas camera={{ position: [0, 2.6, 8.6], fov: 38 }} dpr={[1, 2]}>
        <ambientLight intensity={0.5} />
        <pointLight position={[3.5, 3, 4]} intensity={14} color="#9FC2D6" distance={16} decay={2} />
        <pointLight position={[-3, 1, -3]} intensity={6} color="#2E9C8E" distance={12} decay={2} />
        <Scene specimens={specimens} onHover={setHovered} />
      </Canvas>

      <div className="readout panel" aria-live="polite">
        {hovered ? (
          <>
            <code className="slug">{hovered.slug}</code>
            <span className="stage">{hovered.label}</span>
            {hovered.failure && <span className="fail">{hovered.failure}</span>}
          </>
        ) : (
          <span className="idle label">Hover a specimen</span>
        )}
      </div>

      <style>{`
        .vessel { position: relative; height: clamp(360px, 52vh, 540px); }
        .vessel canvas { display: block; }
        .readout {
          position: absolute; right: 0; top: 0;
          display: flex; flex-direction: column; gap: 0.25rem;
          padding: 0.7rem 0.9rem; min-width: 250px; max-width: 340px;
          pointer-events: none;
        }
        .readout .slug { font-size: var(--t-small); color: var(--ink); }
        .readout .stage { font-size: var(--t-micro); color: var(--accent);
          font-family: var(--font-mono); letter-spacing: 0.1em; text-transform: uppercase; }
        .readout .fail { font-size: var(--t-micro); color: var(--ink-soft); }
        .readout .idle { color: var(--ink-faint); }
      `}</style>
    </div>
  );
}
