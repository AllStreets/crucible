/** Shared by the server layout and the client toggle, so it carries no "use client". */
export const THEME_KEY = "crucible-theme";
export const THEME_EVENT = "crucible-theme";

/** Runs in <head> before first paint, so a light-mode visitor never sees a dark flash. */
export const THEME_BOOT = `try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;
