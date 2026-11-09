# Stage1A protocol v1.0 — frozen before solver execution

Authority: current user explicitly authorizes this separate Stage1 branch, superseding the older root's no-expansion instruction only for the declared horizon/burden campaign. Root governance, Stage0, round3, manuscript and PDFs remain untouched. All writes confined to ECM_STAGE1_LONG_HORIZON_BRIDGE_v1_0. Current reader authority0929; SOURCE_MAPPING_PENDING does not block computation. No Origin, final figure, manuscript prose, new theorem/algorithm, network, nonlinear, stochastic, physical/HIL or LLM work.

## Scientific model and implementation lineage

Exact source constants: P=1/2 MW, Elo=3/25 MWh, Ehi=57/100 MWh, knee=27/50 MWh, auxiliary drain7/1000 MW, eta_d=1, rho=1, beta_c=50/3, beta_d=25/3. eta_c in13/20,9/10,1; h in1/60,1/12,1/4 hour (pressure panel only1/60,1/4). Query is the entire device net trajectory p=d-c; source's q=c-d is its negative, a bijective sign convention, not a query change.

Relaxed variables ordered c[0:T],d[0:T],E[0:T]. E_t=E_(t-1)+h(eta*c_t-d_t-aux); c,d>=0; c+d<=P; Elo<=E_t<=Ehi. At both START and END endpoints: N has (c-d)+bc E<=bc Ehi and (d-c)-bd E<=-bd Elo. G replaces the first flow term byc and second byd. The unique exclusive reconstruction C=max(c-d,0),D=max(d-c,0) and its energy trajectory use exactly the same dynamics.

Initial source60 e0=9/25. Boundary-relative e0=27/50-T*h*(eta/2-7/1000)-3/1000; e1=e0+gain. Eligibility checks both states and the actual single exclusive full-charge native action. No clipping, replacement or tuning of invalid initial conditions; both state slots remain NOT_APPLICABLE in design accounting.

New code has independent storage and versioned lineage; no round3 module imported or executed. model.py extends source native equations; checker.py R1 follows affine-row epigraph/finite positive-sign transform, R2 follows rational native-row SMT reconstruction, R3 follows all-sign reference. Source/protocol hashes recorded in IMPLEMENTATION_LINEAGE.json. Algebra identity QA uses arbitrary rational vectors only, not scientific model samples.

## Frozen matrix and routes

Regression T2:36 pairs/72 states, softwareQA only.
Phase2 T4,6,8,12,16,24:36 pairs each.
Phase2B T5,7,10,14,20:36 pairs each.
Phase3 T32,48,96:12 source60 pairs each,3eta ×2h ×2forms.
ConditionalPhase4 T128,192,256:the same12-pair panel, no T beyond256.
Total predeclared slots504 pairs/1008 states including regression and conditional cells; new scientific design468 pairs/936 state slots. Invalid/inapplicable or conditionally skipped slots remain in denominator.
EligibleT<=8: R2 then R1 then R3. EligibleT>8: R2 then R1; R3 marked SKIPPED_BY_PREDECLARED_RULE. Fixed order applies identically to repetitions. Routes run serially; no solver superiority inference.

## Endpoint and margin semantics

R1 retains the original AUTO_PRESERVED rule v>=0 elementwise. Remaining rows use a negative-absolute epigraph and enumerate positive-absolute signs, exactly as the existing route. Planned count=1 feasibilityLP + sum2^(positive terms) over nonautomatic rows. At regressionT2 all6T existing SOC/power targets are explicitly optimized to reproduce the legacy signed maximum. No arbitrary first-witness early stop.

After regression, a completed positive maximum over checked rows is also the global target maximum because every skipped automatic row has upper bound0. A nonpositive checked-row result with skipped targets does NOT produce a signed global maximum: global-value field is null with NOT_COMPUTED_COMPLETE_TARGET_SET. Skipped automatic constraints are not new solver cases; this preserves existing logic instead of forcing redundant exponential work. Partial best values after timeout are lower bounds, never completed maxima.

R3 enumerates all2^T sign regions and all nonautomatic targets (all targets for regression). It also computes the existing SOC-constrained power maximum at permittedT<=8. AboveT8 this maximum is explicitly uncomputed: exact SMT retains the existing SOC-pass/power-fail existence query and its witness, but no new optimizer is introduced. Fields remain present with availability labels. Raw mixed-unit residuals are not distance, safety, risk or robustness scores. Witness excess is distinguished from an optimized maximum.

## Solver and resource settings

Use the existing Python 3.12 runtime and original dependency directories read-only; -B disables bytecode writes. Frozen environment records actual versions/binary hashes; HiGHS version obtained programmatically. No installation, PATH, Python-environment, registry, power or sleep setting changes.
HiGHS via SciPy linprog:methodhighs, presolveTrue, threads1, primal/dual feasibility1e-7, IPM optimality1e-8. Decision threshold1e-8; regression/route comparison absolute tolerance1e-7, fixed before execution. Remaining state wall budget passed as per-call time_limit; no post hoc tolerance changes.
R2 total budget300 seconds per state including three sequential queries/building; each check receives the remaining shared budget. Z3 random_seed0, max_memory768MB to limit resource pressure. Timeout/UNKNOWN reason retained. Queries: relaxed nonempty, any reconstructed bad native target, SOC-admissible power violation. EMPTY logically implies both bad queriesUNSAT and is recorded as such. A saved exact bad-query witness can establish nonemptiness even if the separate feasibility query was UNKNOWN.
R1 precomputed subproblem budget262144/state. Exceeding it means BUDGET_EXCEEDED without starting enumeration. Per-state working budget1800seconds; supervisor1830seconds allows30seconds interpreter/process overhead only, not a larger solver budget. No campaign-wide time cutoff. Free-disk reserve2GiB; preflight expected output allowance20GiB. Below128MiB available physical memory before a state is a global resource blocker; no external process is killed. Serial workers only.

## Decision and regression gates

STRICT_CERTIFIED requires a saved rational witness passing all relaxed inequalities/equalities and violating a recovered native row. SMT rational witnesses checked with Fraction. LP witnesses may be exactly rechecked using decimal rationals, then denominator bound1e9; no optimization repair and no constraint tolerance in the rational check. Failed reconstruction stays FLOAT_WITNESS_ONLY, never certified.
EQ_CERTIFIED requires exact relaxedSAT and exact badUNSAT. EMPTY_CERTIFIED requires exact relaxedUNSAT. LP nonpositive alone never certifiesEQ. An exact state decision can coexist with a timed-out secondary route/query: record both, not overwrite a valid certificate with genericTIMEOUT.
T2 compares all36 pairs/72 states against original feasibility, bad_smt, SOC_pass_power_fail_smt, all-targetLP maximum, SOC-valid powerLP maximum, first-action and stale-GO labels. Every saved legacy exact witness is reapplied to the generalized model; coordinates of independently found nonunique witnesses need not be identical. No independent new sample count. Any unexplained exact mismatch or endpoint difference>1e-7 immediately writesFAIL and stops globally; no automatic code repair and continuation.
During later phases, decided LP/exact or R1/R3 discrepancies and losslessSTRICT are saved and trigger global semantic review/stop. Ordinary per-caseUNKNOWN/TIMEOUT/BUDGET/ERROR/EMPTY do not stop the campaign. No deletion of negative outcomes.

## Continuation and runtime repetition

Phase2→2B automatic after regressionPASS and preflightPASS. PressureT32→48→96 follows user rule: stop escalation only if all eligible states have both routes limited toUNKNOWN/TIMEOUT/BUDGET and no exact certificate. Record remaining pressure slots as predeclared skips. All-ERROR is not evidence saturation.
EnterPhase4 only after reachingT96 with at least oneEQ, certifiedSTRICT, or completedR1 eligible result. Stop extension after two consecutive extension horizons meeting the same all-unresolved and no-completedR1 condition; otherwise proceed throughT256. Conditional unentered cells remain explicitly skipped.
Runtime panel frozen before any scientific solve:for each T in4,8,12,16,24,32 and eta indexei=0,1,2,row indexri=0,1, choose h=[1/60,1/4][(ei+ri)%2], old/new=[old,new][(ei+ri+T//4)%2], source60. This deterministic stratification yields36 states spanning everyT,eta,row and both durations/states without result selection. One warmup plus5 measured repetitions per state,216 executions total. Same input/hash/options/timeouts/hardware/implementation; no new model samples. Save all outcomes, label censored observations, no solver superiority claim. Total supervised state slots1224; each has three route-accounting slots even ifR3 skipped.

## Persistence, retries, preflight and stopping

State results written atomically without replacement, followed by SHA256 receipt and flushed progress row. Pair checkpoint written after both states. Resume checks input/result/implementation/environment hashes and skips committed matching outcomes, including explicitly unresolved outcomes; never reruns completedPASS cells. Existing mismatched data is a conflict, not overwritten. Attempts/partials retained separately. Any needed result repair requires a newversion.
Transient launch/lock/worker-crash/write failures allow at most2 retries with identical frozen input/options/budget. Persistent failures recordedERROR_PERSISTENT and next cell continues. Semantic assertions/invalid exact witnesses are global failures, not transient retries. Global frozen-hash conflict, unrecoverable environment/disk/memory condition, user stop or specified completion/saturation rule are valid campaign stopping reasons.
Heartbeat every15seconds with required statuses, current phase/horizon, counts, checkpoint, elapsed wall time, disk/memory. Progress CSV flushes per committed state. Final expected-vs-completed table covers state and route cells; no unexplained missing. Operational logs/checkpoints are not scientific sample records.
Phase2 preflight reads time,cwd,executable,environment hash,versions,disk,RAM,CPU,writability and checkpoint/resume tests. powercfg is read-only; any sleep risk is logged only. No cleanup of originals. Output-writability test observes access and prior successful Stage1 checkpoint writes; no probe writes outsideStage1.

## Final production boundary

Generate required evidence tables, conservative existing-data consolidation, tidy visualization datasets, dictionary, availability assessments, QA and12-question allocation report. Do not create final figures or manuscript sentences. Protect all Stage0/round3 assets with before/after hashes; retain reference PDFs at their original locations. STAGE1_STOP is not PROJECT_STOP; await a separate task for Origin/figures/manuscript.
