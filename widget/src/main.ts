// Entry point: the IIFE build exposes window.Perch.
import { identify } from "./widget";

declare global {
  interface Window {
    Perch: { identify: typeof identify };
  }
}

window.Perch = { identify };
