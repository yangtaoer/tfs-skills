# Sichuan deployment audit

Verified on 2026-10-15 (Asia/Shanghai). Canonical machine-readable records are stored in each pipeline's `deploymentAudit` in `../../tfs-project-catalog/references/project-catalog.seed.json`. Refresh them with `../scripts/audit_tfs_deployments.py`; configuration may change after this audit.

## Verified inventory

All linked SSH deployment targets below resolve to `192.168.62.39:22`. The application context is `/netorder` in all eight external configuration files.

| Project | Build | Release | Automatic after Build | Directory | HTTP port | Port evidence |
|---|---:|---:|---|---|---:|---|
| 四川省调网络发令 | 1974 | 53 | Yes | `/home/devczp/scczp` | 8581 | Running process/listener |
| 成都网络发令 | 1972 | 62 | No | `/home/devczp/sccdczp` | 8608 | Running process/listener |
| 资阳调度运行指挥平台 | 8442 | 527 | Yes | `/home/devczp/sczyczp` | 58389 | Running process/listener |
| 南充网络发令 | 1956 | 61 | No | `/home/devczp/scncczp` | 8600 | Running process/listener |
| 宜宾网络发令 | 5489 | 232 | Yes | `/home/devczp/scybczp` | 8609 | External configuration only; no listener observed |
| 巴中网络发令 | 7100 | 450 | Yes | `/home/devczp/scbzczp` | 18080 | Running process/listener |
| 泸州网络发令 | 7096 | 367 | No | `/home/devczp/sclzczp` | 28608 | Running process/listener |
| 乐山网络发令 | 6495 | 331 | No | `/home/devczp/sclsczp` | 8591 | External configuration only; no listener observed |

No linked classic Release was found for 阿坝 (7065), 遂宁 (7945), 广安 (5481), 甘孜 (9596), or the four 自贡检修计划智能编排 definitions (9479, 9480, 9180, 9181). Enabled Build steps and referenced task groups were also inspected: they package, encrypt, publish artifacts, or clean up; no application deployment was found. This does not rule out independently managed deployments.

## Trigger and deployment behavior

The four automatic Releases use an `artifactSource` trigger for the exact Build artifact with no branch/tag conditions. Their environment starts on `ReleaseStarted`, uses automatic approval, and has no schedule or deployment gates. Do not confuse an automatic environment inside a manually created Release with an automatic Build-to-Release trigger.

The eight linked Releases download `drop`, SSH to the target, stop the application, delete old `dcsd-springboot-*.jar` files, copy the new package to the listed directory, then invoke the directory's `service.sh` to start/restart. Encryption machines and the `192.168.62.28` build agent are not deployment targets.

There is no configured periodic deployment interval. For Sichuan provincial Build 1974, eight retained Releases observed on 2026-10-15 showed approximately 4.0–6.4 seconds from Build completion to Release creation and 5.6–8.1 seconds to deployment phase start. These are historical measurements, not guaranteed delays.

The eight server-side service scripts wait 5 seconds after a normal stop before force-killing a remaining process; `restart` pauses 1 second, and startup waits 12 seconds before checking the process. None of these scripts checks HTTP readiness. The provincial application's last observed startup took about 48 seconds, so a successful Release may precede application readiness. Its extra Netty listener is 21687.

## Read-only maintenance

- Resolve by Build ID and TFS project ID; names can be stale or shared across environments.
- Resolve SSH service connection IDs to their actual host; verify that host by login when authorized. Store metadata only, never endpoint authorization data or passwords.
- Verify the deployment directory against Release copy tasks and the service script. Map the running Java process by `/proc/<pid>/cwd`, then inspect its own listeners.
- Prefer external `application-<profile>.properties` to JAR defaults. Record configuration-only ports as such if no matching process/listener exists.
- Do not queue a Build, create a Release, restart services, or change remote configuration during inventory maintenance.
- The runner reports `deploymentMonitoring: not-included-in-build-monitoring`; use the matching Build ID in a Release's artifact version when checking a deployment result. Do not assume the newest Release belongs to the requested Build.
