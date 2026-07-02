# ADR-003: Build System

**Status:** Accepted  
**Date:** 2026-07-01  
**Author:** Andrei

---

## Context

The code universe uses three languages across four domains:

- C/C++ — game engine, shared libs, embedded nodes (ESP32/Arduino)
- Rust — robot nodes (RPi), Tauri desktop apps, hyphoria-rs
- TypeScript/AssemblyScript — plugins, Tauri frontend

Each language has its own native build system. The question is how to unify them — or whether to unify at all — so that mixed-language projects build cleanly and the conventions are consistent across all projects.

Current state: all C/C++ projects use abcmake (CMake module providing component-based structure). All Rust projects use Cargo natively. They have never been in the same build graph.

---

## Requirements

- C++ and Rust can be built together when they live in the same project
- Rust static libs linkable from C++ without manual steps
- C++ static libs linkable from Rust without manual steps
- Cross-compilation to RPi (aarch64) and ESP32 supported
- Pure C++ projects stay pure CMake — no Rust toolchain required
- Pure Rust projects stay pure Cargo — no CMake required
- abcmake conventions are not disrupted

---

## Decision

**Three build systems, each owning its domain. Corrosion as the bridge for mixed projects.**

### Per-domain build system

```
Domain              Build system        Notes
──────────────────────────────────────────────────────────
C/C++ projects      CMake + abcmake     unchanged
Rust projects       Cargo               native, no CMake
Mixed C++/Rust      CMake + abcmake     Corrosion adds Rust
                    + Corrosion         crates as CMake targets
ESP32 / Arduino     CMake + ESP-IDF     no Corrosion, no Cargo
                    or Arduino IDE
TS / AS plugins     npm / asc           separate from CMake/Cargo
```

Pure projects stay pure. Only mixed C++/Rust projects get Corrosion.

### What Corrosion does

Corrosion imports Rust crates from a `Cargo.toml` as first-class CMake targets. A Rust static lib becomes linkable via `target_link_libraries` exactly like any other CMake target. abcmake does not need to know Corrosion exists — it sees a CMake target.

```cmake
# In CMakeLists.txt of a mixed project
include(FetchContent)
FetchContent_Declare(Corrosion
    GIT_REPOSITORY https://github.com/corrosion-rs/corrosion.git
    GIT_TAG v0.6)
FetchContent_MakeAvailable(Corrosion)

# Import hyphoria-rs as a CMake target
corrosion_import_crate(MANIFEST_PATH rust/Cargo.toml)

# abcmake component links it like any other lib
add_main_component(game_engine)
target_link_libraries(game_engine PUBLIC hyphoria_rs)
```

### Direction: C++ calls Rust

Rust crate declares `crate-type = ["staticlib"]` in `Cargo.toml`. Corrosion builds it. C++ links via `target_link_libraries`. C++ calls via the C ABI header (`hyphoria_c.h`). No CMake changes to the C++ side.

### Direction: Rust calls C++

C++ lib is built as a CMake static lib target. Corrosion's `corrosion_link_libraries(rust_target cpp_lib)` links it into the Rust build. Rust calls via `unsafe` FFI block over the C ABI header. `bindgen` can auto-generate the Rust FFI block from the C header as a Cargo build script.

### cbindgen for hyphoria-c

`hyphoria-rs` exposes a C ABI via `cbindgen`. Corrosion has experimental cbindgen integration — `cbindgen.toml` configured to emit `hyphoria_c.h` as part of the CMake build. This keeps the C header in sync with the Rust implementation automatically.

### Mixed project layout convention

```
my-mixed-project/
    components/
        my-cpp-lib/         ← abcmake component
        hyphoria-core/      ← abcmake component (submodule)
    rust/
        hyphoria-rs/        ← Cargo crate
        my-rust-lib/        ← Cargo crate
        Cargo.toml          ← Cargo workspace root
    CMakeLists.txt          ← abcmake root + Corrosion
```

Corrosion is opt-in: only activated when a `rust/` directory exists. Pure C++ projects never see it.

```cmake
# Conditional Corrosion — only if rust/ exists
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/rust/Cargo.toml)
    include(FetchContent)
    FetchContent_Declare(Corrosion ...)
    FetchContent_MakeAvailable(Corrosion)
    corrosion_import_crate(MANIFEST_PATH rust/Cargo.toml)
endif()
```

### ESP32 / Arduino — stays separate

ESP-IDF uses its own CMake wrapper (idf.py). Arduino has its own IDE/CLI. Neither integrates with Corrosion or abcmake in a useful way. ESP32 projects are standalone — they use hyphoria-esp as a plain C++ component added via ESP-IDF component manager or git submodule. No Cargo involvement.

### TypeScript / AssemblyScript — stays separate

Plugin builds (`asc plugin.ts -o plugin.wasm`, `tsc`, `npm run build`) are not part of the CMake or Cargo graph. They run independently and output `.wasm` or `.js` files dropped into the plugins directory. No integration needed.

### Cross-compilation to RPi

CMake toolchain file sets the C++ cross-compiler. Corrosion picks up the Rust target triple from the toolchain file or an explicit variable:

```cmake
# In toolchain file or CMakeLists.txt
set(Rust_CARGO_TARGET aarch64-unknown-linux-gnu)
```

Cargo cross-compilation requires the target to be installed:

```bash
rustup target add aarch64-unknown-linux-gnu
```

The RPi Rust target triple is `aarch64-unknown-linux-gnu`. This must be set in the toolchain file for any mixed project targeting RPi.

---

## Alternatives Considered

**Single build system — everything in CMake**  
CMake can invoke Cargo via `ExternalProject_Add` or `add_custom_command`. Works but is fragile — Cargo's incremental build is bypassed, dependency tracking is manual, and IDE integration breaks. Corrosion solves this properly. Rejected.

**Single build system — everything in Cargo**  
Cargo can invoke CMake via build scripts (`build.rs`). Works for simple cases. Breaks down for complex C++ projects with multiple components, ESP32 targets, and abcmake conventions. Rejected.

**Meson**  
Supports both C++ and Rust natively. Would replace abcmake and Cargo workspace conventions. Rejected because it requires rewriting all existing abcmake projects and abandoning abcmake investment. Not worth it.

**Just keep them separate forever**  
No Corrosion, no integration. C++ projects and Rust projects never share a build graph — they just share binaries via the C ABI at runtime. Simpler, but means hyphoria-rs and hyphoria-core can't be in the same build when needed. Accepted as the default for pure projects; Corrosion is additive for mixed ones.

---

## Consequences

**Positive:**
- Pure C++ projects unchanged — no Rust toolchain required
- Pure Rust projects unchanged — no CMake required
- Mixed projects get a clean integration with ~15 lines of CMake
- abcmake conventions are fully preserved — Corrosion targets look like any other CMake target
- cbindgen integration keeps `hyphoria_c.h` in sync automatically
- Cross-compilation path is explicit and repeatable

**Negative:**
- First build of mixed projects is slow — CMake configures, then Cargo builds, sequentially
- Corrosion version pinning must be maintained — `GIT_TAG v0.6` will go stale
- RPi cross-compilation requires both a C++ cross-toolchain and `rustup target add aarch64-unknown-linux-gnu` — two steps, easy to forget
- ESP32 stays completely separate — no path to unify without significant effort

**Constraints:**
- Mixed projects always have `rust/Cargo.toml` as the Cargo workspace root. No scattered `Cargo.toml` files at project root.
- Corrosion is fetched via `FetchContent`, not installed globally — reproducible across machines.
- Pure projects never pull in Corrosion. The conditional `if(EXISTS rust/Cargo.toml)` guard is mandatory.
- ESP32 projects are always standalone CMake + ESP-IDF. No exceptions.

---

## Open Questions

- abcmake extension for Rust — should `target_link_components` be extended to auto-detect and link Rust crates by name, hiding the Corrosion call? Low priority, current explicit approach is fine.
- Cargo workspace structure across repos — if hyphoria-rs and a robot node are in separate repos, how do they share a Cargo workspace for unified builds? Likely a workspace-per-project approach with path or git dependencies. Decide when the first multi-repo mixed build is needed.
