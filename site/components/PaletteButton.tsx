"use client";

export function PaletteButton() {
  return (
    <button type="button" className="cmdk" aria-label="open navigation"
      onClick={() => window.dispatchEvent(new Event("crucible:palette"))}>
      <span>Go to</span><span className="kbd">cmd</span><span className="kbd">K</span>
    </button>
  );
}
