import '@testing-library/jest-dom/vitest';

// jsdom doesn't implement scrollIntoView
Element.prototype.scrollIntoView = () => {};

// Provide a working localStorage for all tests
const _store: Record<string, string> = {};
const _localStorage: Storage = {
  getItem: (k: string) => _store[k] ?? null,
  setItem: (k: string, v: string) => { _store[k] = v; },
  removeItem: (k: string) => { delete _store[k]; },
  clear: () => { for (const k of Object.keys(_store)) delete _store[k]; },
  get length() { return Object.keys(_store).length; },
  key: (i: number) => Object.keys(_store)[i] ?? null,
};
Object.defineProperty(globalThis, 'localStorage', { value: _localStorage, writable: true });
