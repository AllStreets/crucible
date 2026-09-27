export interface Readout { label: string; value: number | string; sub?: string; tone?: "hot" | "cool" | "warn" | "artifact" }

/** The strip a console shows before anything else. Every value is a count
 *  handed in by the page; the component knows nothing about where it came
 *  from and never invents one. */
export function Telemetry({ items }: { items: Readout[] }) {
  return (
    <div className="telemetry" role="list">
      {items.map((it) => (
        <div key={it.label} role="listitem">
          <span className="label">{it.label}</span>
          <span className={`val ${it.tone ?? ""}`}>{it.value}</span>
          {it.sub && <span className="sub">{it.sub}</span>}
        </div>
      ))}
    </div>
  );
}
