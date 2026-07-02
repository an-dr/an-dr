# ADR-005: Log Reader and Serial Client (microread)

**Status:** Accepted  
**Date:** 2026-07-01  
**Author:** Andrei

---

## Context

The universe has microlog as the canonical logging library across all domains — games, robotics, desktop apps, and embedded. Logs currently go to console or file per-node, with no unified view across nodes and no way to see logs from embedded devices (ESP32, Arduino) alongside logs from networked nodes (RPi, desktop).

Three separate consumption surfaces are needed, each serving a different workflow moment:

- **Tauri app** — full GUI, rich filtering, while investigating a specific problem
- **CLI** — terminal streaming, scriptable, CI-friendly, always available
- **VS Code plugin** — inline, while actively writing code

The tool that serves all three surfaces is **microread** — a log aggregator with two ingestion paths (Zenoh for networked nodes, serial for embedded/early-boot nodes) and a proxy daemon that feeds all consumers.

microread is the companion to microlog. It completes the observability loop: microlog emits, microread receives.

---

## Scope

microread covers:

- Log aggregation from Zenoh (`log/#` topics) and serial ports
- Log ingestion from JavaScript/TypeScript plugins via WebSocket (VS Code extensions, Obsidian plugins)
- Serial as a bidirectional channel: read logs, send commands
- A proxy daemon that normalizes all sources into one stream
- CLI consumer: `microread tail`, `microread dump`, `microread send`
- VS Code extension: live log panel + inline source decorations
- Tauri app: full GUI log viewer (first desktop app in the universe)
- microlog extension: `ulog_hyphoria.h` — registers Hyphoria as a microlog output target
- `@an-dr/microread-js` — shared npm package for logging from any JS/TS plugin

---

## Decision

**microread is a Rust project consisting of four components:**

```
microread/
    proxy/      ← daemon: ingests Zenoh + serial + WebSocket, serves WebSocket
    cli/        ← terminal consumer of proxy WebSocket
    vscode/     ← VS Code extension (TypeScript)
    app/        ← Tauri log viewer (Rust + TypeScript)
```

Plus one microlog extension (lives in the microlog repo) and one npm package:

```
microlog/extensions/
    ulog_hyphoria.h    ← registers Hyphoria as microlog output target
    ulog_serial_structured.h  ← structured framing for serial transport

@an-dr/microread-js  ← npm package, WebSocket logger for JS/TS plugins
```

### Component: microread-proxy

The keystone. A Rust daemon that:

- Subscribes to `log/#` on Zenoh via hyphoria-rs
- Reads one or more serial ports (plain text or structured framing)
- Normalizes all inputs into a single `LogEvent` struct
- Broadcasts JSON `LogEvent` messages to all connected WebSocket clients
- Emits control messages: `node_connected`, `node_disconnected`, `proxy_status`

```rust
struct LogEvent {
    timestamp_ms: u64,
    level:        u8,        // 0=trace..7=fatal
    node_id:      String,    // from Zenoh topic or --node arg
    file:         String,    // __FILE__ from microlog
    line:         u32,       // __LINE__ from microlog
    topic:        Option<String>,  // microlog topic (subsystem)
    message:      String,
    source:       Source,    // Zenoh | Serial(port_name)
}
```

WebSocket message format (JSON):

```json
{
  "type": "log",
  "ts": 1234567890,
  "level": 2,
  "node": "game-engine",
  "file": "src/render.cpp",
  "line": 42,
  "topic": "Renderer",
  "msg": "Entity spawned: 42",
  "source": "zenoh"
}
```

Control messages:

```json
{ "type": "node_connected",    "node": "esp32/imu", "source": "serial:/dev/ttyUSB0" }
{ "type": "node_disconnected", "node": "esp32/imu" }
{ "type": "proxy_status",      "nodes": ["game-engine", "robot/lidar", "esp32/imu"] }
```

Default WebSocket port: `7373`. Configurable.

The proxy accepts **incoming** log messages from WebSocket clients (JS plugins) in addition to broadcasting outgoing messages. When a client sends a JSON message of `type: "log"`, the proxy redistributes it to all other consumers identically to Zenoh-sourced events. This enables JS/TS plugins to participate in the same log stream as C++/Rust nodes.

### Package: @an-dr/microread-js

Shared npm package. Zero dependencies. Works in VS Code extensions, Obsidian plugins, Tauri frontends, and any TypeScript/JavaScript environment that supports WebSocket.

```typescript
import { MicroreadLogger } from "@an-dr/microread-js";

const log = new MicroreadLogger("vscode/my-extension");

log.info("Plugin activated");
log.warn("Config missing, using defaults", "Config");
log.error("Command failed: " + err.message, "Commands");
```

Behavior:
- Connects to proxy at `ws://localhost:7373` on construction
- Buffers messages while disconnected, flushes on reconnect
- Auto-reconnects with exponential backoff (max 30s interval)
- Falls back to `console.log` if proxy never connects (dev machines without proxy)
- `file` and `line` fields are empty — JS has no `__FILE__`/`__LINE__`
- `topic` parameter maps to microlog topic for filtering parity

Node ID convention for JS plugins:
```
vscode/<extension-name>
obsidian/<plugin-name>
tauri/<app-name>
browser/<app-name>
```

The package is the same size as its content — a single TypeScript file, no build step for consumers.

### Component: microread CLI

```bash
microread tail                          # all nodes, all levels
microread tail --node game-engine       # filter by node
microread tail --level warn             # filter by level
microread tail --topic Network          # filter by microlog topic
microread tail --format json            # machine-readable output
microread tail --serial /dev/ttyUSB0    # serial node only
microread tail --serial auto            # auto-detect USB microcontroller

microread dump --since 60s              # dump last 60s to stdout
microread dump --since 60s > debug.log  # save to file

microread send --node esp32/imu "reboot"        # serial command
microread send --node esp32/imu --serial /dev/ttyUSB0 "set_rate 10"

microread proxy                         # start proxy daemon explicitly
microread proxy --port 7374             # custom port
```

`microread tail` auto-starts the proxy if not running. CLI connects to proxy WebSocket.

### Component: VS Code extension (microread-vscode)

TypeScript extension that connects to proxy WebSocket at `ws://localhost:7373`.

**Feature 1 — Output panel:**
A dedicated "microread" output channel tab. Streams live logs colored by level. Filterable by node/level via VS Code command palette.

**Feature 2 — Inline source decorations:**
When a log event carries `file:line` matching a file open in the editor, the last log message appears as a faded inline annotation:

```cpp
ulog_info("Entity spawned: %d", id);   // ℹ  Entity spawned: 42  (2s ago)
ulog_error("Null pointer in render");  // ✕  LAST ERROR  (500ms ago)
```

Implemented via VS Code `DecorationOptions` API. Annotations update in real time as new log events arrive. Error/warn decorations use a colored gutter icon.

**Feature 3 — Status bar:**
```
● game-engine  ● robot/lidar  ○ esp32/imu   ✕ 2 errors
```
Colored dots per node. Red on unacknowledged errors. Click to open log panel filtered to that node.

**Feature 4 — Serial port picker:**
Command palette: `microread: Connect Serial Port`. Lists available ports with VID/PID identification. Connects the proxy to that port, assigns a node name.

### Component: Tauri log viewer (microread-app)

First Tauri desktop app in the universe. Rust backend connects to proxy WebSocket (or runs its own proxy if none is running). TypeScript frontend renders:

- Virtual-scrolling log table (timestamp, node, level, topic, message)
- Filter bar: node multi-select, level checkboxes, free-text search
- Node graph sidebar: dots per node, activity pulse, click to filter
- Log correlation: highlight events within a configurable time window across nodes
- Export: save filtered view to file

### Serial transport

Two modes, selected per port:

**Plain text** (default): parses existing microlog `ulog_event_to_cstr` output. No firmware changes. Works with any device already using microlog. Regex-based parser, handles partial lines.

**Structured** (opt-in): compact binary framing. Faster to parse, supports full `ulog_Event` fields including topic. Requires `ulog_serial_structured.h` extension on the device.

Frame format:
```
[0xAB][len: u16 LE][MessagePack payload][0xCD]
```

MessagePack payload carries the same fields as `LogEvent`. No heap allocation on device — 256-byte stack buffer.

Serial is bidirectional. `microread send` writes UTF-8 lines to the serial port. The device interprets these as commands (device-defined protocol). microread does not define the command protocol — that is application-specific.

### microlog extension: ulog_hyphoria.h

Lives in `microlog/extensions/`. Registers Hyphoria as a microlog output target:

```c
// Usage: one line in node initialization
ulog_hyphoria_add(hyphoria_node, "log/game-engine", ULOG_LEVEL_INFO);
```

Implementation: `ulog_output_handler_fn` callback that serializes `ulog_Event` into a 256-byte stack buffer using MessagePack and calls `hyphoria_publish_async()`. Non-blocking — publish goes to Hyphoria's internal lock-free queue. No heap allocation. Guarded by `#ifdef ULOG_BUILD_HYPHORIA`.

### Topic naming

Log topics follow the `log/` prefix convention (separate from `typed/`, `plugin/`, `raw/`):

```
log/<node_id>
```

Examples:
```
log/game-engine
log/robot/lidar
log/esp32/imu
log/tauri-app
log/vscode/my-extension
log/obsidian/my-plugin
```

This requires adding `log/` as a fourth topic prefix in ADR-002 (messaging system).

---

## Alternatives Considered

**One app (Tauri only, no CLI or VS Code)**  
Simplest. Rejected because CLI is needed for CI and headless server use, and VS Code inline decorations provide the highest-value developer experience — both require the proxy architecture anyway, so the incremental cost of CLI and VS Code extension is low.

**Direct Zenoh subscription in VS Code extension**  
No proxy needed. Rejected because running a Zenoh session inside VS Code's extension host is too heavy and would require Rust in a Node.js context (NAPI or WASM). The proxy is cleaner and enables the CLI and Tauri app to share the same session.

**syslog / journald**  
Standard on Linux. Rejected because: Windows support, embedded support (ESP32 has no syslog), and no structured access to `file:line` or microlog topics. microlog's output is richer than syslog.

**OpenTelemetry**  
Industry standard for observability. Rejected for now — too heavy for embedded targets, adds significant dependencies. microread can export to OpenTelemetry format as a future plugin if needed.

---

## Consequences

**Positive:**
- Single `microread tail` command shows logs from all nodes regardless of transport
- JS/TS plugins (VS Code, Obsidian, Tauri) join the same log stream as C++/Rust nodes via `@an-dr/microread-js`
- Inline VS Code decorations eliminate context switching during development
- Serial support covers embedded nodes with zero firmware changes (plain text mode)
- Bidirectional serial makes microread a general embedded REPL, not just a log viewer
- Tauri app establishes the pattern for all future desktop apps in the universe
- Proxy architecture means one Zenoh session shared by CLI, VS Code, and Tauri app
- microlog extension is one header file, zero changes to microlog core
- `@an-dr/microread-js` is one file, zero dependencies, works in any JS environment

**Negative:**
- Proxy must be running for CLI and VS Code to work — adds a daemon to the dev workflow
- Plain text serial parser is fragile on partial reads and noisy serial lines
- VS Code inline decorations require `file:line` in log events — only available when microlog is built with `ULOG_BUILD_SOURCE_LOCATION=1` (the default)
- `log/` prefix needs to be added to ADR-002 topic convention

**Constraints:**
- `ulog_hyphoria.h` extension uses no heap allocation. Fixed 256-byte stack buffer. Mandatory.
- Serial command protocol is application-defined. microread only provides the transport.
- Generated files from serial structured mode are validated against the same `LogEvent` schema as Zenoh-sourced events. No special cases per source.
- microread-proxy auto-starts when CLI is invoked if no proxy is detected on port 7373.
- The `log/` topic prefix is reserved. No other Hyphoria messages use `log/` as a prefix.
- `@an-dr/microread-js` falls back to `console.log` silently when proxy is unreachable. Never throws. Never blocks.
- JS log events have empty `file` and `line` fields. The log viewer must handle this gracefully — no decoration, no source link, but message is shown normally.

---

## Updates Required in Other ADRs

- **ADR-002** — add `log/` as fourth topic prefix: `log/<node_id>` → MessagePack log events
- **ADR-000** — add microread to observability section, add `@an-dr/microread-js` to shared infrastructure

---

## Implementation Order

1. `ulog_hyphoria.h` — microlog extension, enables Hyphoria output (1 evening)
2. `microread-proxy` — Zenoh ingestion + WebSocket server (1 weekend)
3. `microread tail` CLI — connects to proxy, plain text output (1 evening)
4. Proxy incoming WebSocket ingestion — accepts log messages from JS clients (1 afternoon)
5. `@an-dr/microread-js` — npm package, WebSocket logger for JS/TS plugins (1 evening)
6. Serial plain text ingestion in proxy — parses existing microlog output (1 evening)
7. `microread send` CLI — writes to serial port (1 afternoon)
8. VS Code extension — output panel + status bar (1 weekend)
9. VS Code inline decorations (1 weekend)
10. `ulog_serial_structured.h` + structured framing parser (1 weekend)
11. Serial auto-detect by VID/PID (1 afternoon)
12. Tauri log viewer app — virtual scroll table + filters (2 weekends)
13. Log correlation across nodes (1 weekend)
