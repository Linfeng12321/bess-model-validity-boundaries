# Optional research reruns

This page identifies retained research implementations and fixed inputs. Use a disposable copy and the [recorded environment](../ENVIRONMENT.md) for a solver run. Campaign drivers can write results and depend on their original directory organization. The [quickstart](reviewer_quickstart.md) checks saved evidence without launching those drivers.

## Source entries

Paths below are relative to the repository root. Directory names and program names retain their original versions and import relationships.

| Study | Source directory and programs | Inputs and setup |
|---|---|---|
| Original horizon study | [implementation_v1_0](../code/original_layout/ECM_STAGE1_LONG_HORIZON_BRIDGE_v1_0/implementation_v1_0/): `checker.py`, `model.py` | [Internal saved states](../data/Internal_Saved_States.jsonl); original protocol, configuration and campaign layout |
| Literature device mapping | [00_GOVERNANCE](../code/original_layout/ECM_STAGE2B_DEEP_EXTERNAL_CLOSURE_v1_0/00_GOVERNANCE/): `mapping.py`, `verifier_v1_1.py` | [External saved states](../data/External_Saved_States.jsonl); retained terminal adapter and Z3 for logical decisions |
| Exact domains | [round3](../code/original_layout/RESEARCH/round3/): `check_closed_region_and_transition.py`, `run_parametric_region_pilot.py` | [Twelve obligations](../data/Boundary_Check_Specification.json); linear programming (LP) and satisfiability modulo theories (SMT) packages |
| Later horizon certificates | [Strengthening scripts](../extensions/source_layout/ECM_TARGETED_STRENGTHENING_20261017/SCRIPTS/): `run_lossless_certificates.py`, `certification_routes.py`, `run_certification_study.py` | Same 936 inputs and 152 certificate inputs; generating new candidates uses numerical and logical libraries |
| Three bus dispatch | [Strengthening scripts](../extensions/source_layout/ECM_TARGETED_STRENGTHENING_20261017/SCRIPTS/): `run_system_study.py`, `system_model.py` | 13 registered pairs and 26 results; economic, primary service and secondary cost encodings remain distinct |
| Complete network model | [Deep research sources](../extensions/source_layout/ECM_AUTONOMOUS_DEEP_RESEARCH_20261018/): `model.py`, `network.py`, `classify_network.py`, `route_extension.py` | Normalized 24 hour input, native rows and eight set certificates |
| Original numerical network requests | [Original drivers](../extensions/source_layout/ECM_AUTONOMOUS_DEEP_RESEARCH_20261018/00_AUTHORITY_CONTROL/FAILURE_SOURCES/): `run_system_stress.py`, `system_model.py`, `independent_physics.py` | [Saved numerical runs](../extensions/source_layout/ECM_AUTONOMOUS_DEEP_RESEARCH_20261018/00_AUTHORITY_CONTROL/PREVIOUS_CORE/03_SYSTEM_FINAL/RUNS/); original fixed inputs retained |
| Price driven policy | [original_simulation_policy.py](../code/original_simulation_policy.py) | [Recorded policy](../data/Simulation_Policy.json), states and included price response; driver performs work on import |

The network uses the Reliability Test System of the Grid Modernization Laboratory Consortium (RTS-GMLC). Original numerical request generation, nearby exact recovery and complete set certification are separate routes and versions. [Certificate definitions](numerical_certificates.md) identify their respective evidence.

## Environment and access

The original recorded environment used Python 3.12.14, NumPy 2.3.5, SciPy 1.16.2, HiGHS 1.8.0 and Z3 4.15.3 on Windows 11. Solver options remain in [Recorded_Environment.json](../Recorded_Environment.json). Later network routes also used cvc5 and SymPy; take their versions from the route records rather than the current installation.

The [external data guide](external_data_access.md) identifies included price and system inputs and separate measurement access. Original source entries require route specific setup; they are not a portable single command campaign. Reproducing computation times on different machines requires a separate comparison.
