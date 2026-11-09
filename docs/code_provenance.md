# Research implementations

The source tree retains 67 inherited Python programs with their versioned names and import relationships. Three additional release engineering programs provide environment, manifest and regression checks. Their file identities are in the [release manifest](../release_manifest/SHA256SUMS.csv); the complete 67 program provenance table is preserved as [source program identities](../release_manifest/SOURCE_PROGRAM_IDENTITIES.csv).

## Find a scientific component

| Research component | Implementation entry | Data and reader action |
|---|---|---|
| Energy dynamics and exclusive reconstruction | [internal_model.py](../code/internal_model.py) | Inspect native rows and the [saved state inputs](../data/Internal_Saved_States.jsonl) |
| Literature device formulations | [external_mapping.py](../code/external_mapping.py) | Follow [34 instance definitions](../data/External_Instances.csv) and [source mappings](../data/Source_Mapping_Details.json) |
| Analytical validity domains | [Domain checker](../code/original_layout/RESEARCH/round3/check_closed_region_and_transition.py) | Inspect [declared obligations](../data/Boundary_Check_Specification.json) and [saved outcomes](../data/Boundary_Quantified_Results.json) |
| Original horizon certification | [Original checker](../code/original_layout/ECM_STAGE1_LONG_HORIZON_BRIDGE_v1_0/implementation_v1_0/checker.py) | Follow [assessments](../data/Internal_Assessments.csv), [pairs](../data/Internal_Pairs.csv) and original route settings |
| Later exact certificates | [Arithmetic checker](../extensions/source_layout/ECM_TARGETED_STRENGTHENING_20261017/SCRIPTS/audit_exact_results.py) | Inspect [certificate identities](../extensions/certification/152_EXISTING_CERTIFICATE_IDENTITIES.csv) and their [proof routes](numerical_certificates.md) |
| Three bus economic and service requests | [System model](../extensions/source_layout/ECM_TARGETED_STRENGTHENING_20261017/SCRIPTS/system_model.py) | Compare [registered settings](../extensions/synthetic/REGISTERED_SYSTEM_CASES.json) with selected request records |
| Complete network model | [Network implementation](../extensions/source_layout/ECM_AUTONOMOUS_DEEP_RESEARCH_20261018/network.py) | Inspect [certificate status](../extensions/rts/RTS_EXACT_CERTIFICATE_STATUS.csv) and retained native rows |
| Price driven operating policy | [Policy source](../code/original_simulation_policy.py) | Read [policy parameters](../data/Simulation_Policy.json) and [simulation records](../data/Source_Driven_Simulation.csv); this driver executes work on import |
| Saved evidence verification | [Combined entry](../scripts/verify_release.py) | Run the command in the [quickstart](reviewer_quickstart.md) |

The combined entry uses the supplied model builders and saved evidence wrappers. Research campaign drivers retain their original directory assumptions. The [optional rerun guide](optional_full_research_rerun.md) identifies the original implementations and additional dependencies.

## Source identity and reuse

The source identity table retains each original functional label, relative path and SHA256 value. A source hash identifies a program version; it does not establish individual authorship or legal ownership. Copyright notices remain intact. [License information](../LICENSE_INFORMATION.md) separates author code from upstream terms.
