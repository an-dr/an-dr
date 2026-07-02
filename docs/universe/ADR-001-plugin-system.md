# ADR-001: Plugin System Architecture

**Status:** Accepted  
**Date:** 2026-07-01  
**Author:** Andrei

---

## Context

The unified ecosystem spans four domains: games (C++ SDL engine), desktop apps (Rust + Tauri), robotics (Rust nodes on RPi), and embedded devices (C++ on ESP32/Arduino). All domains need a plugin/extension mechanism that:

- Allows new features without recompiling the core
- Works identically across C++ and Rust hosts
- Supports both high-performance and rapid-iteration use cases
- Follows the Obsidian model: drop a file, reload, feature appears

The scripting layer must not couple plugin authors to a single language, and must not require a full toolchain to write simple behavior scripts.

---

## Decision

**Two-tier plugin system built on WebAssembly (Wasm).**

### Tier 1: Compiled plugins (.wasm)

Plugin authors write in any language that compiles to Wasm (AssemblyScript, Rust, C++). Output is a `.wasm` file dropped into the plugins directory. The host loads and runs it via wasmtime.

Use for: performance-critical systems, complex logic, anything that needs near-native speed.

### Tier 2: Interpreted plugins (.js)

QuickJS compiled to Wasm ships as part of the engine. Plugin authors write plain JavaScript (or TypeScript transpiled via `tsc`). No build step. Edit the file, reload, done.

Use for: behavior scripts, configuration-driven logic, rapid iteration, modding.

### Runtime

Both tiers run inside **wasmtime**. QuickJS is just another `.wasm` file the host loads once. The engine has one runtime dependency regardless of plugin type.

### API contract

All plugins (compiled and interpreted) share the same interface defined in a **WIT file** (WebAssembly Interface Types). `wit-bindgen` generates host bindings for C++ (`wasmtime-c`) and Rust (`wasmtime` crate), and plugin-side bindings for AssemblyScript and Rust. The WIT file is the single source of truth for the plugin API.

```wit
package myengine:plugin@0.1.0;

world plugin-world {
    import engine-api;  // services plugins can call
    export plugin;      // interface plugins must implement
}
```

### Hot reload

Plugins reload at frame/tick boundary on explicit trigger or file change detection. Lifecycle: `on_unload()` → file reload → `on_init()`. No mid-frame swaps.

---

## Alternatives Considered

**Lua (sol2)**  
Simpler to embed in C++. Mature, fast, controllable GC. Rejected because it only works in C++ — no clean story for Rust apps. Would require two scripting systems.

**TypeScript via V8**  
Full TypeScript support, excellent AI codegen. Rejected because V8 is a 20MB+ dependency with a complex embedding API and no native Wasm story. QuickJS covers the interpreted use case at a fraction of the cost.

**Rhai**  
Pure Rust, clean embedding, Rust-like syntax. Rejected because it has no C++ embedding story. Good fit for Rust-only projects but breaks the unified cross-language requirement.

**Raw Wasm (no WIT)**  
Simpler initial setup. Rejected because manual FFI for complex types (strings, structs, enums) across the host/guest boundary is error-prone and not maintainable. WIT + wit-bindgen solves this at the cost of one additional tool.

**Shared libraries (.so / .dll)**  
Maximum performance, full language access. Rejected because: no sandboxing, platform-specific, ABI instability across compiler versions, no cross-language story without a C ABI layer.

---

## Consequences

**Positive:**
- One runtime (wasmtime) works in both C++ and Rust hosts
- Plugin authors choose their language freely
- Interpreted path (QuickJS) requires zero build toolchain for simple scripts
- WIT enforces a typed, versioned API contract
- Same `.wasm` plugin format works across game engine, desktop app, and robot nodes
- Natural performance tiering: compile when it matters, interpret when speed of iteration matters

**Negative:**
- AssemblyScript is TypeScript-like but not full TypeScript — some TS patterns don't compile to Wasm
- Host↔guest function calls have ~100ns overhead — not suitable for per-frame hot paths
- Wasm Component Model (WIT) is a 2024 spec — tooling is stable but younger than alternatives
- QuickJS-in-wasmtime bridge requires a custom adapter layer (non-trivial, one-time build)
- wasmtime adds ~5MB to binary size

**Constraints:**
- Per-frame hot-path logic stays in C++/Rust core. Plugins handle event-driven and behavior logic only.
- WIT file is versioned (`@major.minor.patch`). Breaking API changes require a version bump.
- QuickJS.wasm ships as part of the engine distribution. Plugin authors do not supply their own JS runtime.

---

## Implementation Order

1. Define `plugins.wit` — API contract, versioned
2. Wasmtime host in C++ engine (`wasmtime-c`) — compiled plugin loading
3. Wasmtime host in Rust apps (`wasmtime` crate) — same
4. QuickJS.wasm integration — interpreted plugin loading
5. JS↔WIT adapter — maps QuickJS exports to WIT plugin interface
6. Hot-reload file watcher — triggers reload at safe boundary
7. AssemblyScript plugin template — starter for compiled TS-like plugins
8. Rust plugin template — starter for compiled Rust plugins
9. JS plugin template — starter for interpreted plugins
