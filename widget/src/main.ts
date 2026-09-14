// Perch embeddable widget. Built as an IIFE exposing window.Perch.
// v1 scaffold: real WebSocket + UI lands in task 3.

export {};

interface PerchApi {
  identify: (info: { name?: string; email?: string }) => void;
}

const state: { name?: string; email?: string } = {};

const api: PerchApi = {
  identify(info) {
    Object.assign(state, info);
  },
};

(window as unknown as { Perch?: PerchApi }).Perch = api;

console.log("[perch] widget loaded", state);
