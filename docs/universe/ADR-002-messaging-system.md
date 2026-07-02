# ADR-002: Messaging System (Hyphoria)

**Status:** Accepted  
**Date:** 2026-07-01  
**Author:** Andrei

---

## Context

The unified ecosystem spans four domains and multiple languages:

- Games — C++ SDL engine with ECS, Windows/Linux. Also used for robot simulation.
- Desktop apps — Rust + Tauri, cross-platform
- Robotics — Rust nodes on Raspberry Pi (Linux), C++ nodes on ESP32/Arduino
- Embedded — C++ on ESP32 and Arduino

Nodes in this ecosystem need to communicate within a process, between processes on the same machine, and across machines on a LAN. The messaging system must work uniformly across C++ and Rust without requiring app code to change when the transport changes.

An existing project, **Hyphoria** (`github.com/an-dr/hyphoria`), already implements the right abstraction: a C++ messaging framework that decouples app code from eventing backends. This ADR extends that foundation to cover all messaging requirements.

---

## Requirements

- Pub/sub and request/reply patterns
- Works in C++ and Rust without duplicating logic
- Covers same-process, same-machine (IPC), and LAN transports
- Transport is swappable without changing app code
- Serialization is pluggable and decoupled from transport
- Works on Linux, Windows, macOS, Raspberry Pi, ESP32
- No mandatory broker or central server

---

## Decision

**Extend Hyphoria as the universal messaging layer for all domains.**

### Architecture

```
hyphoria-core (C++)
    canonical implementation
    abstract IBackend + ISerializer interfaces

hyphoria-c
    C ABI wrapper over hyphoria-core
    stable FFI boundary for all non-C++ consumers

hyphoria-rs
    Rust crate — native implementation using Zenoh directly
    NOT a thin FFI wrapper (see rationale below)

hyphoria-esp
    Lightweight C++ subset for ESP32/Arduino
    uses zenoh-pico as transport backend
```

### Why native Rust, not FFI wrapper

A thin Rust wrapper over the C ABI is the low-effort path, but it has a structural problem: C FFI callbacks do not compose with Rust async (`tokio`). Bridging them requires a non-trivial adapter layer (callback → tokio channel), adds latency, and produces un-idiomatic Rust that will resist maintenance.

Since Rust is the primary language for robot nodes and desktop apps — the two most active domains — the friction cost is real and ongoing. A native Rust implementation using Zenoh directly satisfies the same API contract as `hyphoria-core` while being fully `async/await` compatible and idiomatic.

The C ABI layer (`hyphoria-c`) remains the bridge for C++ → Rust interop where needed, but `hyphoria-rs` does not depend on it.

### hyphoria-rs sync API

Non-async Rust contexts (Tauri sync commands, thread-based robot nodes) need to call `hyphoria-rs` without `async/await`. The pattern is a tokio runtime running alongside the sync context, bridged via `tokio::sync::mpsc`:

```
tokio runtime (background thread)
    runs Zenoh subscriptions
    sends messages into mpsc::Sender

sync context (main thread / game tick)
    polls mpsc::Receiver each tick
    converts to internal events / ECS components
```

No separate sync backend needed. One runtime, one bridge channel per node.

```
InProcessBackend    tokio broadcast channels (Rust)
                    or lockless queue (C++)
                    ~50-100ns, same process only
                    use for intra-node communication

ZenohBackend        Zenoh pub/sub + queryable
                    covers same-machine AND LAN transparently
                    uses shared memory automatically for local peers
                    autodiscovery, no broker, cross-platform
                    works identically on Windows and Linux

ZenohPicoBackend    zenoh-pico C library
                    ESP32/Arduino embedded target
                    same Zenoh bus, same topics
```

### Transport selection policy

```
same thread / task              →  in-process channels (tokio / std)
same process (C++)              →  InProcessBackend (lockless queue)
cross-process, same machine     →  ZenohBackend (shared memory auto)
cross-machine / LAN             →  ZenohBackend (peer-to-peer UDP/TCP)
ESP32 / Arduino                 →  ZenohPicoBackend
```

App code calls `Hyphoria::publish()` and `Hyphoria::subscribe()`. Backend selection happens at node initialization via config or build target. App code does not change.

Zenoh is the single transport for all cross-process communication regardless of whether nodes are on the same machine or different machines. Platform-specific IPC (Unix sockets, Windows named pipes) is not used — Zenoh's shared memory transport covers the same-machine case on all platforms without platform-specific code.

### Serialization

Serialization is decoupled from transport via `ISerializer`. Two serializers ship with Hyphoria, each in its own lane:

- **Cap'n Proto** — typed messages, schema-defined, zero-copy reads. Used for all typed inter-node communication where both sides know the schema at compile time: robot telemetry, game events, node commands. Generates C++ and Rust bindings from a single `.capnp` file.
- **MessagePack** — schemaless, dynamic, no codegen. Used for plugin messages, QuickJS/JS output, config passing, and any message where the schema is unknown or defined at runtime. Excellent TypeScript support via `msgpack-javascript`.
- **Raw bytes** — passthrough. Caller owns the format. Used internally when a higher-level serializer is wrapping the payload.

The serializer is signaled by topic path convention, not per-message metadata:

```
typed/...   →  Cap'n Proto   (e.g. robot/lidar/scan, game/entity/spawned)
plugin/...  →  MessagePack   (e.g. plugin/quickjs/output, plugin/config/set)
raw/...     →  Raw bytes     (e.g. raw/audio/stream)
log/...     →  MessagePack   (e.g. log/game-engine, log/robot/lidar, log/esp32/imu)
```

`log/` is reserved for microlog events routed via the `ulog_hyphoria.h` extension and consumed by microread. Subscribers deserialize based on topic prefix. No out-of-band negotiation required.

### Topic schema ownership

All valid topic strings are defined in a single file — `topics.h` in `hyphoria-core`. This is the canonical source of truth. No topic string is typed as a raw literal anywhere in application code.

```cpp
// hyphoria-core/include/hyphoria/topics.h
namespace Topics {
    // typed/ — Cap'n Proto serialized, inter-node
    constexpr auto GAME_ENTITY_SPAWNED   = "typed/game/engine/entity_spawned";
    constexpr auto GAME_ENTITY_DESTROYED = "typed/game/engine/entity_destroyed";
    constexpr auto ROBOT_LIDAR_SCAN      = "typed/robot/lidar/scan";
    constexpr auto ROBOT_IMU_READING     = "typed/robot/imu/reading";
    constexpr auto APP_COMMAND_SHUTDOWN  = "typed/app/command/shutdown";

    // plugin/ — MessagePack serialized, dynamic
    constexpr auto PLUGIN_QUICKJS_OUTPUT = "plugin/quickjs/output";
    constexpr auto PLUGIN_CONFIG_SET     = "plugin/config/set";

    // raw/ — passthrough bytes
    constexpr auto RAW_AUDIO_STREAM      = "raw/audio/stream";
}
```

**Language coverage:**

- C++ — uses `topics.h` directly. All domains depending on `hyphoria-core` get it for free.
- Rust — `topics.rs` mirrors the same constants. A format validation test asserts every string matches `^(typed|plugin|raw)/[a-z_]+/[a-z_]+/[a-z_]+$`.
- TypeScript — `topics.ts` generated by a small Python script from `topics.h`. Run as part of the Tauri frontend build.

**Rule:** adding a new topic means editing `topics.h` first, then regenerating `topics.rs` and `topics.ts`. Never add a topic string directly in application code.



Four methods. This is the complete app-facing API in both C++ and Rust:

```
publish(topic, payload)
subscribe(topic, callback)
request(topic, payload) -> Future<payload>
reply(ctx, payload)
```

Topic format: `domain/node_id/subject`  
Examples: `game/engine/entity_spawned`, `robot/lidar/scan`, `app/ui/command`

### Language coverage

```
C++ apps          hyphoria-core directly
C++ → Rust FFI    hyphoria-c (C ABI, opaque handle + free functions)
Rust apps         hyphoria-rs (native, tokio-async)
TypeScript        via Wasm bridge or Deno FFI over hyphoria-c
ESP32 / Arduino   hyphoria-esp (C++, zenoh-pico backend only)
```

---

## Alternatives Considered

**Zenoh directly (no Hyphoria abstraction)**  
Simpler, fewer layers. Rejected because it couples all app code to Zenoh's API. Switching transports (e.g. to ZeroMQ or a future embedded transport) requires touching every node. Hyphoria's backend abstraction is the point.

**ZeroMQ as primary transport**  
Battle-tested, mature C++ library, bindings everywhere. Rejected as primary because it requires manual service discovery — nodes must know each other's addresses in advance. For a dynamic multi-machine setup (robot joins the network, desktop app discovers it automatically), this requires building a registry layer that Zenoh provides for free. Remains a viable `IBackend` implementation if Zenoh's C++ bindings prove unstable on a target.

**Bevy (Rust game engine) for robot simulation**  
Considered as a simulation and game platform. Rejected because the C++ SDL engine already has ECS, a renderer, and the full game loop. Bevy's primary value proposition was ECS + renderer — both already exist in the C++ engine. Adding Bevy would mean a second game framework with its own plugin system conflicting with the decided Wasm plugin architecture. The C++ engine covers games, robot simulation (headless mode via build flag), and game tools from one codebase.
Industry standard for robotics, solves discovery and transport. Rejected because: colcon/ament build system is Linux-only in practice, Windows support is incomplete, the framework is invasive (owns your main loop and node model), and it would not cover games or desktop apps. Hyphoria + Zenoh covers the same transport/discovery needs without the constraints.

**Unix sockets / Windows named pipes for local IPC**  
Faster than Zenoh for same-machine cross-process (~1-5μs vs ~10-50μs). Rejected because they are platform-specific — Unix sockets don't exist on Windows, named pipes have a different API. Handling both requires `#ifdef` inside the backend, adding maintenance cost for a latency difference that is invisible at game and robotics timescales. Zenoh's shared memory transport covers the same-machine case cross-platform with acceptable performance. Remains an option if benchmarks show Zenoh local latency is a bottleneck.

**Thin Rust FFI wrapper over hyphoria-c**  
Low effort, shares the C++ implementation. Rejected as the primary Rust path because C FFI callbacks are incompatible with Rust async without a non-trivial adapter. Since Rust is primary for robot nodes and Tauri apps, this friction is daily. Native implementation is the right call. The C ABI layer is still built for cases where C++ code needs to call into Rust or vice versa.

---

## Consequences

**Positive:**
- Single API (`publish`, `subscribe`, `request`, `reply`) across all four domains
- Transport swappable at init time — no app code changes
- Zenoh covers same-machine and LAN with one backend — no platform-specific IPC code (no Unix socket vs named pipe split)
- Zenoh shared memory transport handles local peers automatically — no manual transport selection per deployment
- Zenoh autodiscovery — robot node and desktop app find each other on LAN with zero config
- `hyphoria-rs` is fully async-native — no callback bridge friction in Rust code
- ESP32 nodes join the same Zenoh bus via `zenoh-pico` — same topics, same messages
- Cap'n Proto + MessagePack split covers all message types cleanly — typed nodes use schemas, plugins use dynamic encoding
- Topic prefix convention encodes serializer — no per-message metadata overhead, no out-of-band negotiation

**Negative:**
- Two implementations (C++ core + native Rust) — API contract must be kept in sync manually
- zenoh-cpp maturity on embedded Linux targets needs validation early
- Two serializers (Cap'n Proto + MessagePack) — developers must know which lane a message belongs to
- Cap'n Proto schema tooling is an additional build dependency
- Cap'n Proto binary format is hard to debug without tooling — need a `capnp decode` step in the debug workflow

**Constraints:**
- Topic keyspace is `domain/node_id/subject`. No freeform topics.
- RT-critical control loops (robot actuators, game physics) do not use Hyphoria. They use direct function calls or lock-free queues internal to the node. Hyphoria is for inter-node communication only.
- ZeroMQ is not used in the initial implementation but `IBackend` must be implementable by it — this validates the abstraction is not Zenoh-specific.
- The C++ engine exposes a `ENGINE_HEADLESS` build flag that strips the SDL renderer. Headless mode is used for robot simulation on RPi and CI behavior testing. ECS, physics, and Hyphoria remain active in headless mode.

---

## Open Questions

- Zenoh local latency validation — benchmark Zenoh shared memory transport on target machines before shipping. If same-machine latency is a bottleneck, `LocalBackend` with `#ifdef` is the fallback (Unix socket on Linux, named pipe on Windows).

---

## Implementation Order

1. `IBackend` + `ISerializer` interfaces in `hyphoria-core` — defines the abstraction
2. `InProcessBackend` (C++) — lockless queue, validates the interface
3. `ZenohBackend` (C++) — covers local + LAN, validates both transport cases
4. `hyphoria-c` — C ABI wrapper, enables all non-C++ consumers
5. `hyphoria-rs` — native Rust, tokio-async, ZenohBackend via `zenoh` crate
6. Cap'n Proto serializer — typed message support, generate C++ + Rust bindings from `.capnp`
7. MessagePack serializer — dynamic message support, C++ (`msgpack-cxx`) + Rust (`rmp-serde`)
8. `hyphoria-esp` — ESP32 target, zenoh-pico backend
9. Zenoh local latency benchmark — validate shared memory transport on target hardware
10. Cross-language smoke test — C++ publisher (Cap'n Proto), Rust subscriber, same topic
11. Cross-machine smoke test — RPi node, laptop subscriber
12. Plugin integration smoke test — JS plugin sends MessagePack over `plugin/` topic, Rust app receives
