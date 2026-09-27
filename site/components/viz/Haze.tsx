"use client";

import { useEffect, useRef } from "react";

/** Heat haze behind the opening statement: a slow fractal-noise field in the
 *  furnace palette, rendered at low resolution and scaled up. Atmosphere, not
 *  information, so it carries no data and makes no claim. Static under
 *  reduced motion, paused when the tab is hidden. */
const VERT = `attribute vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }`;
const FRAG = `
precision mediump float;
uniform vec2 r; uniform float t; uniform vec2 m;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
float fbm(vec2 p){ float v = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { v += a * noise(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; } return v; }
void main(){
  vec2 uv = gl_FragCoord.xy / r; vec2 q = uv * vec2(r.x / r.y, 1.0);
  float d = distance(uv, vec2(0.62, 0.18) + (m - 0.5) * 0.08);
  float n = fbm(q * 2.2 + vec2(t * 0.045, -t * 0.03)) * 0.8 + fbm(q * 5.0 - t * 0.02) * 0.2;
  float heat = smoothstep(1.05, 0.0, d) * (0.35 + 0.65 * n);
  vec3 cold = vec3(0.043, 0.043, 0.051);
  vec3 ember = vec3(0.894, 0.388, 0.165);
  vec3 white = vec3(1.0, 0.72, 0.45);
  vec3 col = cold + ember * heat * 0.55 + white * pow(heat, 3.0) * 0.35;
  col += (hash(uv * r + t) - 0.5) * 0.012;
  gl_FragColor = vec4(col, 1.0);
}`;

export function Haze() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current; if (!canvas) return;
    const gl = canvas.getContext("webgl", { antialias: false, alpha: false, powerPreference: "low-power" });
    if (!gl) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const sh = (type: number, src: string) => { const s = gl.createShader(type)!; gl.shaderSource(s, src); gl.compileShader(s); return s; };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VERT)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FRAG)); gl.linkProgram(prog); gl.useProgram(prog);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "p"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const uR = gl.getUniformLocation(prog, "r"), uT = gl.getUniformLocation(prog, "t"), uM = gl.getUniformLocation(prog, "m");
    let mouse = [0.5, 0.5], target = [0.5, 0.5], raf = 0, visible = true;
    const size = () => { const w = Math.floor(canvas.clientWidth * 0.5), h = Math.floor(canvas.clientHeight * 0.5); if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; gl.viewport(0, 0, w, h); } };
    const onMove = (e: MouseEvent) => { const b = canvas.getBoundingClientRect(); target = [(e.clientX - b.left) / b.width, 1 - (e.clientY - b.top) / b.height]; };
    const onVis = () => { visible = !document.hidden; if (visible && !reduced) raf = requestAnimationFrame(frame); };
    const start = performance.now();
    const frame = () => {
      if (!visible) return;
      size(); mouse = [mouse[0] + (target[0] - mouse[0]) * 0.04, mouse[1] + (target[1] - mouse[1]) * 0.04];
      gl.uniform2f(uR, canvas.width, canvas.height); gl.uniform1f(uT, (performance.now() - start) / 1000); gl.uniform2f(uM, mouse[0], mouse[1]);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      if (!reduced) raf = requestAnimationFrame(frame);
    };
    window.addEventListener("mousemove", onMove); document.addEventListener("visibilitychange", onVis);
    frame();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("mousemove", onMove); document.removeEventListener("visibilitychange", onVis); };
  }, []);
  return <canvas ref={ref} className="haze" aria-hidden="true" />;
}
