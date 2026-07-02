# ADR-004: File Exclusion System (IGNORE)

**Status:** Accepted  
**Date:** 2026-07-01  
**Author:** Andrei

---

## Context

Every project in the universe needs file exclusion rules — patterns that tell tools which files to skip. Currently each project maintains its own `.gitignore`, and any tool that needs similar exclusion (Docker, npm, build scripts) either duplicates the patterns or goes without.

The problems this causes:

- Pattern drift — `.gitignore` and `.dockerignore` diverge silently
- Manual maintenance — updating patterns in one file doesn't update others
- No structured access — tools can't query "what should I ignore for category X" programmatically
- Per-project reinvention — every project writes the same CMake/Rust/ESP-IDF patterns from scratch

An existing project, **IGNORE** (`github.com/an-dr/IGNORE`), solves this with a structured JSON format that is both the source of truth for generated files and directly consumable by native tools.

---

## The IGNORE Format

IGNORE files are JSON (with comments) validated against `https://ignore.dev/schema/v1.json`. Three sections:

```json
{
  "$schema": "https://ignore.dev/schema/v1.json",

  "ruleSets": {
    "vcs":        [".git/", ".svn/", ".hg/"],
    "build":      ["dist/", "build/", "**/*.js.map"],
    "deps":       ["node_modules/"],
    "editor":     [".vscode/", ".idea/", "**/*.bkp"],
    "os":         ["**/.DS_Store", "**/Thumbs.db"],
    "secrets":    ["**/*.env", "**/.env*", "**/*.key"],
    "cpp-build":  ["build/", "CMakeCache.txt", "CMakeFiles/", "*.o", "*.a"],
    "rust-build": ["target/"],
    "esp-idf":    ["build/", "sdkconfig", "sdkconfig.old", "dependencies.lock"],
    "capnproto":  ["*.capnp.c++", "*.capnp.h"],
    "wasm":       ["*.wasm"],
    "tauri":      ["src-tauri/target/", "dist/"]
  },

  "generate": {
    ".gitignore":    ["@vcs", "@build", "@deps", "@editor", "@os", "@secrets",
                      "@cpp-build", "@rust-build"],
    ".dockerignore": ["@vcs", "@build", "@deps", "@secrets", "@cpp-build",
                      "@rust-build"]
  },

  "native": {
    "hyphoria":     ["@cpp-build", "@rust-build", "@secrets"],
    "game-engine":  ["@cpp-build", "@wasm"],
    "tauri-app":    ["@rust-build", "@tauri", "@secrets"],
    "esp32-node":   ["@esp-idf", "@cpp-build"]
  }
}
```

**`ruleSets`** — named pattern groups. The source of truth. Never referenced directly outside IGNORE.

**`generate`** — declares what files the CLI generates. Values are lists of `@ruleSet` references plus optional literal patterns. The CLI resolves references and writes each output file.

**`native`** — declares what each native tool (your own tools) consumes. Tools parse this section directly — no generation, no intermediate files.

---

## Decision

**IGNORE is the single source of truth for all file exclusion rules across all projects and all tools.**

### Two usage paths

```
IGNORE file
    │
    ├── generate section  →  ignore-cli  →  .gitignore
    │                                    →  .dockerignore
    │                                    →  .npmignore
    │                                    →  (any external tool)
    │
    └── native section   →  your tools read directly
                             no CLI, no generation, no drift
```

External tools (git, Docker, npm) get generated files. Your own tools (hyphoria, game engine, Tauri app, build scripts) read IGNORE natively via `libignore`.

### ignore-cli

A Rust CLI that:

- Reads the `generate` section
- Resolves `@ruleSet` references (flattens to pattern lists)
- Writes each declared output file next to IGNORE
- Supports `--watch` flag (file watcher via `notify` crate) for automatic regeneration on save

```bash
ignore generate          # one-shot
ignore watch             # watch mode
ignore check             # validate IGNORE against schema, report drift
ignore list <tool>       # print patterns for a native tool
```

### libignore

A Rust crate that parses IGNORE and exposes a query API. Used by all native tools.

```rust
pub fn load(path: &Path) -> Result<IgnoreFile, Error>;
pub fn get_generate_patterns(file: &IgnoreFile, output: &str) -> Vec<String>;
pub fn get_native_patterns(file: &IgnoreFile, tool: &str) -> Vec<String>;
pub fn matches(file: &IgnoreFile, tool: &str, path: &Path) -> bool;
```

C ABI wrapper (`libignore_c.h`) follows the standard universe convention — opaque handle, free functions, error codes. C++ tools link it directly.

### Plugin system for generators

Generator plugins handle format differences between tools (e.g. `.npmignore` has slightly different negation semantics than `.gitignore`). Each plugin is a Rust struct implementing:

```rust
trait IgnorePlugin {
    fn name(&self) -> &str;          // e.g. "gitignore"
    fn output_file(&self) -> &str;   // e.g. ".gitignore"
    fn render(&self, patterns: &[String]) -> String;
}
```

Built-in plugins: `gitignore`, `dockerignore`, `npmignore`. Additional plugins added as Rust crates — no Wasm needed, transforms are simple string operations.

### Native tool integration

Tools parse IGNORE at startup or build time:

```rust
// In any Rust tool (hyphoria-rs, tauri app, etc.)
let ignore = libignore::load(Path::new("IGNORE"))?;
let patterns = libignore::get_native_patterns(&ignore, "hyphoria");
// use patterns to filter file operations
```

```cpp
// In any C++ tool (game engine, build scripts)
auto* h = libignore_load("IGNORE");
auto patterns = libignore_get_native_patterns(h, "game-engine");
libignore_free(h);
```

### Per-project IGNORE files

Each project has its own IGNORE file at the project root. It references the universe-standard ruleSets (those are defined in the canonical IGNORE at `github.com/an-dr/IGNORE`) and adds project-specific patterns.

Future option: `@include` directive to pull in the canonical IGNORE ruleSets without copying — deferred until needed.

---

## Alternatives Considered

**`.gitignore` as the single file, copied everywhere**  
Simple. No tooling. Rejected because it only covers git, other tools get nothing, and updating requires touching every project.

**Global `~/.gitignore_global` (machine-level)**  
Zero per-project maintenance. Rejected as primary because it's personal, not committed with the project, and doesn't give tools structured programmatic access.

**`gitignore.io` generated files**  
Good for bootstrapping. Rejected as ongoing solution because it's external, not under your control, and produces flat files with no structure for programmatic access.

**Custom text format (INI-style sections)**  
Simpler to read, no JSON parser needed. Rejected because JSON with schema gives editor validation, autocomplete, and versioning for free via the `$schema` field. The complexity cost is `serde_json` as a dependency — acceptable everywhere in the Rust universe.

**Wasm plugins for generators**  
Consistent with the universe plugin system. Rejected because generator transforms are simple string operations — a Rust trait is sufficient and adds no runtime dependency.

---

## Consequences

**Positive:**
- One file per project, all tools stay in sync automatically
- `.gitignore` and `.dockerignore` are derived, never edited manually — no drift
- Native tools get structured pattern access without generation step
- JSON schema gives editor validation and autocomplete for free
- `ignore check` can detect when generated files are out of sync with IGNORE (CI use)
- Adding a new tool to the universe = add one entry to `native` section

**Negative:**
- JSON with comments is not standard JSON — requires comment-stripping before parsing, or a JSON5 parser
- Every project needs `ignore-cli` installed to generate files (or CI does it)
- `libignore` is another dependency for native tools — small but real
- `@include` for shared ruleSets not yet implemented — each project copies the standard ruleSets

**Constraints:**
- Generated files (`.gitignore`, `.dockerignore`, etc.) are never edited manually. They carry a header comment: `# Generated by IGNORE — do not edit`.
- The `native` section tool names must match the tool's binary name exactly — used as the lookup key.
- IGNORE files are validated against `https://ignore.dev/schema/v1.json` before processing. Invalid files abort with an error.
- Project-specific patterns go in the local IGNORE file, not in the shared canonical IGNORE at `github.com/an-dr/IGNORE`.

---

## Universe-standard ruleSets

These ruleSets are defined in the canonical IGNORE and should be present in every project IGNORE (copied until `@include` is implemented):

| RuleSet | Covers |
|---------|--------|
| `vcs` | Git, SVN, Mercurial metadata |
| `editor` | VS Code, JetBrains, temp files |
| `os` | macOS, Windows system files |
| `secrets` | `.env`, keys, certificates |
| `cpp-build` | CMake build artifacts, object files |
| `rust-build` | Cargo `target/` directory |
| `esp-idf` | ESP-IDF build output, sdkconfig |
| `capnproto` | Generated Cap'n Proto C++ files |
| `wasm` | Compiled `.wasm` plugin output |
| `tauri` | Tauri build output |

---

## Open Questions

- `@include` directive — pull in ruleSets from a remote IGNORE file (e.g. canonical IGNORE) without copying. Implement when per-project copying becomes painful.
- `ignore.dev` domain — the schema `$id` references `https://ignore.dev/schema/v1.json`. Should this be hosted and resolve to the actual schema for editor validation? Low effort, high value.

---

## Implementation Order

1. Universe-standard ruleSets defined in canonical IGNORE — update `github.com/an-dr/IGNORE`
2. `libignore` Rust crate — parse, resolve references, query API
3. `libignore_c` — C ABI wrapper, follows universe convention
4. `ignore-cli` — `generate`, `watch`, `check`, `list` subcommands
5. Built-in plugins — `gitignore`, `dockerignore`
6. Integration in first native tool — hyphoria-core reads IGNORE for build filtering
7. `@include` directive — deferred
