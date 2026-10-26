# Native job resource admission

This is the Code owner's execution envelope, separate from fleet placement prices.
Operations authors measured budgets in each released job declaration. Systems
passes the same declaration through the existing node-job adapter. No job, timer,
credential source, transport or dispatcher is replaced.

A job MAY retain its legacy declaration. A job declaring resources MUST supply
memoryMaxBytes, memorySwapMaxBytes (zero is valid), tasksMax, cpuQuotaPercent,
memoryReserveBytes, and its existing positive finite maxSeconds. Optional
memoryHighBytes MUST be positive and no greater than memoryMaxBytes. Byte values
and task counts MUST be safe integers; unknown fields and nonfinite values refuse.
No heap size, deadline or production budget is inferred from fleet pricing.

Before a fleet bid, runNodeJob MUST receive current Linux MemAvailable and require
memoryMaxBytes + memoryReserveBytes. Unknown or insufficient availability MUST
throw NODE_JOB_RESOURCE_ADMISSION before any bid, demand unlink or native start.
An existing active cohort MUST continue untouched. After an admitted fleet claim,
the runner MUST repeat the reading because claiming may wait. A post-claim refusal
retains that original claim until its existing window expires; it MUST NOT erase,
refund or replay it. Both refusals retain the original receipt and demand bytes.
They remain operation failures, so the original clock does not acknowledge them
as a successful demand occurrence.

The original systemd-run carrier MUST receive exact MemoryMax, MemorySwapMax,
TasksMax, CPUQuota and optional MemoryHigh, plus the existing RuntimeMaxSec.
Native cgroup enforcement bounds the entire job cohort, including its finally and
recorder processes. A budget therefore includes those processes. Kernel limits
may end a job; such an ending retains its ordinary unsuccessful native receipt.
Resources do not establish successful programme completion or drained custody.

MemAvailable is a current host observation, not a reservation, a proof of ancestor
cgroup headroom, or a guarantee against concurrent admissions. Per-job kernel
ceilings remain enforced during races. Deployments needing a shared aggregate
ceiling MUST receive that envelope through their existing native slice/provider
owner; this API MUST NOT claim one exists. Existing MemoryHigh-only drop-ins and
fleet memoryGb prices do not establish a hard shared capacity reservation.

The affected acquisition consumer family MUST separately propagate one authored
deadline/body/concurrency envelope through the existing HTTP acquire-response and
body/web owners. Unread or refused feeds retain their original cursor; bounded
acquisition MUST NOT truncate canonical evidence and claim it was read. Current
Kalshi sources have no evidence identifying which phase caused the observed
120-second native timeout; this source change does not attribute that timeout.

Receiving requires the original fleet/custody/credential/recorder cases plus
declaration refusal, exact native property emission, refusal before bid, capacity
loss while waiting, unchanged authoritative receipt/demand and active-cohort
preservation. Fixture argv acceptance is source qualification; the released
consumer must still receive actual native limits and useful bounded work before
the Operations capacity obligation is complete.
