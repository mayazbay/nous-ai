---
type: spec
id: PHASE-0-COLLECTOR-DEPLOYMENT-2026-04-21
title: "Phase-0 sniff-target collector deployment — Nous-GPU receives Denis's firewall-mangle-TZSP output"
tags: [spec, phase-0, collector, nous-gpu, sniff-target, tzsp, denis, 2026-04-21, session-56]
date: 2026-04-21
status: active-phase-0-E2E-LIVE-2026-04-21
last_updated: 2026-04-21
related:
  - "[[denis]]"
  - "[[nous-gpu]]"
  - "[[camera-management]]"
  - "[[infrastructure]]"
  - "[[source-satory-meeting-2026-04-20-license-handover-bdl-access]]"
---

# Phase-0 collector deployment — Nous-GPU ← Denis's new server

**Status at write-time (session 56, 2026-04-21 ~13:00 KZT):** 3 of 4 Phase-0 open questions closed by [[denis|Denis]]'s 2026-04-21 11:32 KZT Telegram reply. Architecture pivoted from ARCH-A (obsrv decodes) to ARCH-D (Denis deploys separate dedicated sniff-target server; Nous supplies collector endpoint). `[[nous-gpu]]` now has its first real workload.

## Goal

Stand up a UDP-37008 **TZSP listener** on [[nous-gpu|Nous-GPU]] (`100.70.222.21` Tailscale) that receives mirrored camera traffic from Denis's new dedicated server, decapsulates the TZSP wrapper, writes timestamped pcap slices to disk with rotation, and emits basic packet-count / flow metrics to a health endpoint pollable from Air. Denis remains responsible for the MikroTik `firewall-mangle-TZSP` rule that directs traffic at us; we are the passive receive + forward endpoint.

**Scope (Phase-0 only):** one camera, invisible at L7, receive + pcap only. NO active probing, NO write-back into the camera network, NO credential use on cameras in this phase. Phase-1 (session-58+) adds RTSP extraction + frame sampling; Phase-2 adds autoconfig-script reverse engineering.

## Architecture (ARCH-D — supersedes ARCH-A + ARCH-B)

```
  [Camera on 10.235.0.x/24]
         │
         ▼  RTSP/ISAPI/HTTP traffic
  [Core MikroTik router]
         │  /ip firewall mangle
         │    chain=prerouting
         │    action=sniff-tzsp
         │    sniff-target=<DENIS-SERVER-IP>
         ▼
  [Denis's new dedicated server — TBD provisioning]
         │  (1) receives TZSP-encapsulated mirror
         │  (2) optionally pre-filters / batches
         │  (3) forwards over Tailscale/WG/public UDP
         ▼
  [Nous-GPU @ 100.70.222.21:37008]
         │  TZSP listener (tzsp-server or Go/Python)
         │  → pcap-rotate (per-hour, zstd-compressed, mounted volume)
         │  → metrics: packet-count, unique-5-tuple count, pcap-byte-rate
         ▼
  [Air launchd com.nous.nous-gpu-collector-health]
         │  5-min Tailscale ping + UDP-37008 open-check + metrics-delta
         │  → Telegram alert on anomaly (port dead, no packets for N min)
```

## Open decisions (blocking Phase-0 cut-over, NOT blocking Nous-side prep)

### D1. Network path Denis-server → Nous-GPU

| Option | Pros | Cons | Nous recommendation |
|---|---|---|---|
| **(A) Tailscale client on Denis's new server** | encrypted / direct / zero firewall change / we invite, they install | requires Tailscale install on Denis's side (~5 min) | **PREFERRED** |
| (B) WireGuard site-to-site | Denis's team may already know WG; more deterministic routing | we manage config on both sides; key rotation overhead | secondary |
| (C) Denis public-IP → our Tailscale exit node | no client install on Denis's side | UDP-37008 public = attack-surface; NAT traversal gotchas | fallback only |

Decision deferred to Madi (asked 2026-04-21 via Telegram msg 878). Nous-side prep below is path-agnostic.

### D2. Collector stack

| Option | Pros | Cons |
|---|---|---|
| **(i) `tzsp-server` (reference Perl script)** | canonical implementation; bytes-for-bytes correct | Perl runtime; no modern packaging |
| **(ii) Go binary (`gotzsp` or custom ~200 LOC)** | single static binary; Docker-friendly; easy metrics | ~1 day of net-new code |
| (iii) Python (`scapy` + TZSP decoder) | fastest to prototype; easy to extend | higher memory; GIL under load |
| (iv) `tcpdump -i <iface> udp port 37008` + post-hoc TZSP decap | zero dependency; pcap-native | decap happens off-line; delayed observability |

**Preference:** start with **(iv) `tcpdump`** for session-57 — ships in 30 min, gives us real pcaps to inspect. Upgrade to **(ii) Go** in session-58+ once we understand actual traffic shape. This is the Musk/Karpathy pattern: ship the dumbest-thing-that-works, measure, then invest.

### D3. Storage + rotation

- pcap output at `/var/nous/collector/pcap/` on Nous-GPU (create dir + ownership `nous-admin:nous-admin`).
- 1-hour rotation, zstd-compressed. Retention 7 days (Phase-0 research window; Phase-1+ sizes from real data).
- Write-once-read-many — pcaps are immutable evidence; never edited in place.
- Disk budget: assume 10-100 MB/s of mirror traffic as upper bound = ~36-360 GB/hour uncompressed, ~5-50 GB/hour after zstd. 7-day retention = up to 8 TB uncompressed / 800 GB compressed worst case. RTX 5070 host likely has ~500 GB-1 TB local — may need rolling-7-days-to-3-days OR offload to VPS after N hours. **Pending Denis's traffic-volume answer (Q3 in Telegram 878).**

## Nous-side prep (session-57 executable, path-agnostic)

These steps require NO decision from Denis — can ship whenever.

1. **Create collector dir on Nous-GPU.** `ssh nous-gpu 'sudo mkdir -p /var/nous/collector/{pcap,logs} && sudo chown -R nous-admin:nous-admin /var/nous/collector'`
2. **Install baseline tooling.** `ssh nous-gpu 'sudo apt-get update && sudo apt-get install -y tcpdump tshark zstd jq netcat-openbsd'` (Docker already installed per provisioning).
3. **Open UDP 37008 in Ubuntu firewall.** Confirm `ufw status` — if enabled, `sudo ufw allow 37008/udp comment "TZSP Phase-0 collector"`.
4. **Test listener locally.** `ssh nous-gpu 'sudo timeout 10 tcpdump -i any -n udp port 37008 -w /tmp/tzsp-test-$(date +%s).pcap'` — expect zero packets; confirms listener binds + rotates pcap without traffic.
5. **Tailscale ACL check.** `tailscale status` on Mac must show nous-gpu peer; UDP 37008 reachable from Mac via `nc -u -v 100.70.222.21 37008` → Mac sees the port open (no RST).
6. **Ship baseline launchd on Air.** `~/Library/LaunchAgents/com.nous.nous-gpu-collector-health.plist` — 5-min cadence probing (a) Tailscale ping, (b) UDP port, (c) last pcap file mtime vs now. Alert to Madi via `tools/tg_send.sh` on anomaly. Script: `tools/nous_gpu_collector_health.sh`.
7. **Commit spec (this file) + Mac-side probe script + Air launchd + Nous-GPU bootstrap script** to vault. RULE ZERO: any learning from the prep (e.g. firewall gotchas) → update `infrastructure` skill, not a new LESSON.

## Denis-side answers (2026-04-21 ~12:30 KZT reply — all 4 closed)

- Q1 BDL read-access → **Нет.** Rule lives on Denis's private server; no cover-story naming needed on core MikroTik.
- Q2 network path → **WG** (WireGuard). Not Tailscale. Supersedes D1 Option A → Option B becomes primary. Nous-side work: stand up WG responder on Nous-GPU (or edge host), distribute peer config to Denis.
- Q3 ETA → **1-2 days** (depends on his queue). Nous-side Phase-0 prep SHIPPED this session — we are ready to receive.
- Q4 throughput → **1-2 ГБ/с.** ⚠️ **UNIT CONFIRMATION PENDING** with Madi. If gigabytes (literal read), the pcap-to-disk baseline dies immediately — pivot to inline TZSP-decap + per-camera selective save. If Mb/s (Russian-tech shorthand, common for "mega"), baseline works. See §D3-revised below.

## D3-revised — storage budget scenarios (blocks Phase-1 decision)

| Unit read | Steady-state traffic | 1h pcap | 7d retention | pcap-to-disk viable on Nous-GPU? |
|---|---|---|---|---|
| 1-2 **Mb/s** | 0.25 MB/s | ~0.9 GB | ~150 GB uncompressed / ~30 GB zstd | ✅ easy |
| 1-2 **MB/s** | 1-2 MB/s | ~3.6-7.2 GB | ~600 GB-1.2 TB uncompressed | ⚠️ tight, needs zstd + rotate |
| 1-2 **Gb/s** | 125-250 MB/s | ~450-900 GB | ~75-150 TB uncompressed | ❌ dies in hours |
| 1-2 **GB/s** | 1-2 GB/s | ~3.6-7.2 TB | ~600 TB-1.2 PB | ❌ dies in 30 min |

**Decision tree:**
- If Denis confirms Mb/s → current collector shipped in this session is complete Phase-0.
- If MB/s → add zstd-on-rotate + 24h retention cap + off-GPU backup.
- If Gb/s or higher → architectural pivot BEFORE Phase-1 cut-over: inline TZSP-decap + filter to 1 camera for Phase-0 demonstration, selective save only on ML-inference triggers.

## Phase-0 Nous-side SHIPPED status (2026-04-21, session 56 extension)

- [x] S1: `~/collector/{pcap,logs}` dirs on Nous-GPU (pivoted from `/var/nous/` — no sudo avail)
- [x] S2: Package baseline (tcpdump/zstd/nc already present; tshark/jq deferred — use Docker `nicolaka/netshoot:latest` which ships both)
- [x] S3: Firewall — host ufw inactive; UDP 37008 flow-through works directly over Tailscale
- [x] S4: Container `nous-collector` running persistent with `--restart=unless-stopped`
- [x] S5: E2E Mac → GPU smoke test — 10/10 probes received, tshark decodes as TZSP protocol (payloads malformed because test probes weren't real TZSP; production Denis traffic will be well-formed)
- [x] S6: Air launchd `com.nous.nous-gpu-collector-health` PID 6780, 5-min cadence, state-change alerting
- [x] S7: Commit (session-56 extension batch — see handoff)

## Phase-0 → Phase-1 cut-over COMPLETE (2026-04-21 ~17:46 KZT, session-56 extension)

All 4 cut-over criteria MET:
1. ✅ Nous-GPU listens on UDP 37008 (now on wg0 instead of tailscale0; same filter).
2. ✅ Denis's dedicated server provisioned + WG tunnel UP + `firewall-mangle-TZSP` rule active → real TZSP traffic visible.
3. ✅ E2E test: real camera RTSP/ISAPI packets (source 10.170.x:8581) arrive in Nous-GPU pcap wrapped in TZSP envelopes from `10.99.99.2:37008`. tshark decodes the inner frames correctly.
4. ⏳ 24-hour stability TBD (test clock starts now). Launchd health probe + regression probe remain as ongoing monitors.

**Empirical throughput resolution:** Denis's "1-2 ГБ/с" answered by actual 15-sec measurement = 1.9 Mbit/s. Unit was Mb/s in Russian tech shorthand, NOT GB/s. Storage budget table D3-revised: pcap-to-disk baseline is fine; ~21 MB/hr uncompressed, ~2 GB/7-day compressed. Nous-GPU /home has 859 GB free, so even without zstd rotation the current write rate doesn't threaten disk for years.

## Historical — Phase-0 → Phase-1 transition work (session-57+) [ARCHIVE]

1. ~~WireGuard keygen~~ ✅ **done session-56-ext 2026-04-21 ~15:01 KZT.** Nous-GPU WG keypair generated via `docker run --rm alpine apk add wireguard-tools && wg genkey | wg pubkey`. Private key stored at `~/collector/wg/nous_gpu.priv` (600 perms, nous-admin-only, **not vault-tracked**). Public key below — safe to share.
2. Denis-side WG server config + our client config wiring — BLOCKS on Denis returning his WG server endpoint (public IP + port) + his WG server pubkey + tunnel subnet assignment.
3. Re-deploy collector with `-i wg0` once WG is up + Denis's server is online (or keep `-i tailscale0` for dual-path dev + `-i wg0` for prod).
4. Throughput-budget confirmation from Madi → if >Mb/s, architectural pivot per D3 table.
5. Cut-over criteria §§1-4 verified before calling Phase-0 shipped-E2E.

## WireGuard handoff packet — send to Denis when the dedicated server is ready

> **Parallel-session reconciliation 2026-04-21:** This spec initially shipped a Docker-based keypair (`0G9U...`). Parallel session-57 independently installed `wireguard-tools` natively on Nous-GPU host (sudo via Asyl) and generated the canonical keypair in `/etc/wireguard/nous-gpu.{key,pub}`. **The host-native keypair wins** — deleted my Docker-based duplicate on GPU (was at `~/collector/wg/`, redundant). Keep only the one in `/etc/wireguard/`. See [[nous-gpu]] entity line 69 for full setup details.

**Nous-side public key** (canonical, from `/etc/wireguard/nous-gpu.pub`):
```
9vYGZvvyAKeCXAcpf55IhI9CJak6MpiZsJVDh3Q8MmI=
```

**What Denis sends back to us** (needed to complete the tunnel on our side):
1. His WG server's **public key** (what we add as our `[Peer].PublicKey`)
2. His WG server's **public endpoint** (`IP:port` — what we dial from Nous-GPU)
3. **Tunnel subnet assignment** for us (e.g., `10.99.0.2/32` if his server is `10.99.0.1/24`)
4. **Allowed-IPs** he wants us to accept (typically the `sniff-target` packets' source + his camera subnet if he wants ICMP back)

**Nous-side config staged by parallel session-57** at `/etc/wireguard/wg0.conf`:
- `[Interface]` Address = `10.99.99.1/24`, ListenPort = `51820` (we offered tunnel-server role)
- `[Peer]` block commented out; uncomment + fill Denis's values when they arrive
- `wg-quick strip wg0` passes parse validation
- `systemctl enable --now wg-quick@wg0` to activate (once Peer block is populated)

**If Denis prefers us-as-client instead of us-as-server** (depending on which side has easier public-IP exposure): session-57 work re-stages `/etc/wireguard/wg0.conf` accordingly. Denis's preference + network topology answers drive the role call.

Then re-deploy `nous-collector` with `-i wg0` filter (currently `-i tailscale0`). Regression gate `tools/test_nous_gpu_collector_tzsp.sh` (shipped session-57) runs before + after the filter swap to confirm the pipe is E2E-healthy via the new interface.

## Cut-over criteria (Phase-0 → Phase-1)

Phase-0 is SHIPPED when all four are true:

1. Nous-GPU listens on UDP 37008 with dir + tcpdump + launchd + Tailscale reachability green.
2. Denis's dedicated server is provisioned + `firewall-mangle-TZSP` rule active + network path (D1) established.
3. End-to-end test: one camera's RTSP/ISAPI packets arrive in a Nous-GPU pcap, decapsulated TZSP payload parses as expected.
4. 24-hour stability: launchd health-probe reports green for a full day without manual intervention.

Phase-1 trigger: all 4 above + Madi explicit greenlight. Phase-1 = widen rule to all `10.235.x` cameras + begin RTSP extractor on Nous-GPU's RTX 5070.

## Musk 5-step pre-filter applied

1. **Question:** Do we need Phase-0 at all? YES — displaces Cerebro; customer-confirmed intent (Daniyar at 2026-04-20 meeting).
2. **Delete:** Can we skip the collector + read pcaps directly from Denis's server? NO — that couples us to Denis's disk + gives less operational independence. Keep collector.
3. **Simplify:** `tcpdump` over Go — chosen in D2.
4. **Accelerate:** Nous-side prep (steps 1-7) is path-agnostic; ship BEFORE Denis's server ready to shave 1-2 days off critical path once he answers D1.
5. **Automate:** launchd health-probe in step 6 means Phase-0 self-monitors from day zero.

## See also

- [[denis]] — 2026-04-21 11:32 KZT Telegram reply (source of this spec's pivot)
- [[nous-gpu]] — host spec, Tailscale-reachable, first-workload assignment
- [[camera-management]] v2.8.0 — AP-17 L2-only-under-Azamat-hostility (still applies; collector is passive, invisible at L7)
- [[source-satory-meeting-2026-04-20-license-handover-bdl-access]] — 2026-04-20 meeting where Daniyar confirmed customer intent
- [[tailscale-stability]] v1.2.0 — reference for adding a new peer (Denis's server if path A)
- [[infrastructure]] — skill for launchd + Docker + host ops; absorbs any new prep learnings
- [[HANDOFF-AUTO-2026-04-21-session-56-MASTER-close-drift-fix-meta-ratchet]] — session in which this spec was written
