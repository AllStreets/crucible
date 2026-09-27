"use client";

import { useEffect } from "react";

/** Marks sections as they enter the viewport. Everything is visible at rest;
 *  the class only lets CSS ease a section's position and weight in, so a
 *  screenshot, a crawler, and a reader with motion disabled all see the page
 *  whole. */
export function Reveal() {
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    const obs = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); obs.unobserve(e.target); }
    }, { rootMargin: "0px 0px -8% 0px" });
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);
  return null;
}
