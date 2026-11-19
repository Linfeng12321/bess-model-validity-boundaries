# Figures and tables

The archived v1.0.0 source map records nine main figures, four main tables, four Supplementary Material (SM) figures and 28 SM tables. The current manuscript contains ten main figures, including an Introduction overview. The display numbers below follow the current manuscript; stable labels and full archived source bindings remain in the [192 object map](main_sm_code_data_crosswalk.csv). No scientific records have changed.

| Current main figure | Archived v1.0.0 figure | Stable paper label |
|---|---|---|
| 1 | Not included | `fig:intro_overview` |
| 2 | 1 | `fig:related_work_perspectives` |
| 3 | 2 | `fig:methods_query_validity` |
| 4 | 3 | `fig:results_validity_regions` |
| 5 | 4 | `fig:results_state_transition_composite` |
| 6 | 5 | `fig:results_convexification` |
| 7 | 6 | `fig:results_horizon_certification` |
| 8 | 7 | `fig:results_external_evidence` |
| 9 | 9 | `fig:dispatch_request_realizability` |
| 10 | 8 | `fig:discussion_temporal_queries` |

The Introduction overview is conceptual and adds no new numerical evidence; it is not an asset in the archived v1.0.0 source map.

The [figure data](../figure_data/) contain the released display values. Native OriginPro projects and image exports are held separately, except for the grouped [Figure S2 source](../figure_source/SI_RF01_20261109/README.md) included in this revision. Figure S4 measurement trajectories, derived plot data and native graphs are excluded pending redistribution permission. The [external data guide](external_data_access.md) describes access.

## Analytical validity

Sources: [Supplementary_Derivations.tex](../proofs/Supplementary_Derivations.tex), [internal_model.py](../code/internal_model.py), [Boundary_Quantified_Results.json](../data/Boundary_Quantified_Results.json), [Boundary_Grid_Checks.json](../data/Boundary_Grid_Checks.json), [Boundary_Check_Specification.json](../data/Boundary_Check_Specification.json), [check_closed_region_and_transition.py](../code/original_layout/RESEARCH/round3/check_closed_region_and_transition.py), [Exact_Hull_Constructions.json](../data/Exact_Hull_Constructions.json).

| Display | Stable paper label |
|---|---|
| Main Figure 2 | `fig:related_work_perspectives` |
| Main Figure 3 | `fig:methods_query_validity` |
| Main Figure 4 | `fig:results_validity_regions` |
| Main Figure 6 | `fig:results_convexification` |
| Main Table 2 | `tab:validity_conditions` |
| Table S1 | `tab:assumption_roles` |
| Table S2 | `tab:si_certificate_reuse` |
| Table S3 | `tab:boundary_domains` |
| Table S4 | `tab:boundary_grid` |
| Table S12 | `tab:residual_controls` |

## Controlled states and horizons

Sources: [Internal_Pairs.csv](../data/Internal_Pairs.csv), [Internal_Assessments.csv](../data/Internal_Assessments.csv), [Internal_Saved_States.jsonl](../data/Internal_Saved_States.jsonl), [internal_model.py](../code/internal_model.py), [Timing_Repetition_Records.csv](../data/Timing_Repetition_Records.csv), [Repeated_Timing_Summaries.csv](../data/Repeated_Timing_Summaries.csv), [Lossless_Control_Factor_Lookup.csv](../data/Lossless_Control_Factor_Lookup.csv), [Recorded_Environment.json](../Recorded_Environment.json), [checker.py](../code/original_layout/ECM_STAGE1_LONG_HORIZON_BRIDGE_v1_0/implementation_v1_0/checker.py), [152_EXISTING_CERTIFICATE_IDENTITIES.csv](../extensions/certification/152_EXISTING_CERTIFICATE_IDENTITIES.csv), [17_HORIZON_VERSION_ACCOUNTING.csv](../extensions/certification/17_HORIZON_VERSION_ACCOUNTING.csv), [468_PAIR_VERSION_ACCOUNTING.csv](../extensions/certification/468_PAIR_VERSION_ACCOUNTING.csv), [audit_exact_results.py](../extensions/source_layout/ECM_TARGETED_STRENGTHENING_20261017/SCRIPTS/audit_exact_results.py), [verify_extensions_saved.py](../scripts/verify_extensions_saved.py).

| Display | Stable paper label |
|---|---|
| Main Figure 5 | `fig:results_state_transition_composite` |
| Main Figure 7 | `fig:results_horizon_certification` |
| Main Table 3 | `tab:numerical_settings` |
| Figure S1 | `fig:repeated_timing` |
| Figure S2 | `fig:lossless_factors` |
| Table S5 | `tab:internal_parameters` |
| Table S6 | `tab:horizons` |
| Table S7 | `tab:residual_paired_conditions` |
| Table S8 | `tab:transition_vector` |
| Table S9 | `tab:t2_controls` |
| Table S10 | `tab:semantics` |
| Table S11 | `tab:solver_settings` |
| Table S22 | `tab:sat_certificate_types` |
| Table S23 | `tab:si_horizon_followup` |
| Table S24 | `tab:sat_pair_accounting` |

Figure S1 and the original timing records retain the original protocol. Tables S22–S24 give the later certificate routes, final 17 horizon classifications and accounting for the same 468 pairs. These versions are complementary.

## Literature mappings

Sources: [External_Instances.csv](../data/External_Instances.csv), [External_Assessments.csv](../data/External_Assessments.csv), [External_Saved_States.jsonl](../data/External_Saved_States.jsonl), [Source_Mapping_Details.json](../data/Source_Mapping_Details.json), [External_Transitions.csv](../data/External_Transitions.csv), [external_mapping.py](../code/external_mapping.py).

| Display | Stable paper label |
|---|---|
| Main Figure 8 | `fig:results_external_evidence` |
| Main Table 1 | `tab:related_work_comparison` |
| Main Table 4 | `tab:results_evidence_scope_candidate` |
| Table S16 | `tab:source_locators` |
| Table S17 | `tab:external_parameters` |
| Table S18 | `tab:external_transitions` |
| Table S19 | `tab:residual_family_witnesses` |

## Temporal queries

Sources: [Temporal_Query_Classifications.csv](../data/Temporal_Query_Classifications.csv), [Directional_Objective_Values.csv](../data/Directional_Objective_Values.csv), [Two_Interval_Control_Records.json](../data/Two_Interval_Control_Records.json), [Supplementary_Derivations.tex](../proofs/Supplementary_Derivations.tex).

| Display | Stable paper label |
|---|---|
| Main Figure 10 | `fig:discussion_temporal_queries` |
| Figure S3 | `fig:si_temporal_response` |
| Table S13 | `tab:si_temporal_domains` |
| Table S14 | `tab:directions` |
| Table S15 | `tab:si_temporal_values` |

Figure 10 compares temporal query guarantees and directional objective values. Figure 9 concerns selected dispatch requests; its data are distinct.

## Three bus dispatch

Sources: [REGISTERED_SYSTEM_CASES.json](../extensions/synthetic/REGISTERED_SYSTEM_CASES.json), [SYSTEM_STATE_PAIRS.csv](../extensions/synthetic/SYSTEM_STATE_PAIRS.csv), [FIGURE9_26_STATE_SOURCE_MAPPING.csv](../extensions/source_layout/ECM_FIGURE9_STEP2D_REDESIGN_V2_20261023/01_SOURCE_AND_NUMERICAL_QA/FIGURE9_26_STATE_SOURCE_MAPPING.csv), [FIGURE9_SERVICE_ENERGY_EXACT.csv](../extensions/source_layout/ECM_FIGURE9_STEP2D_REDESIGN_V2_20261023/01_SOURCE_AND_NUMERICAL_QA/FIGURE9_SERVICE_ENERGY_EXACT.csv), [system_model.py](../extensions/source_layout/ECM_TARGETED_STRENGTHENING_20261017/SCRIPTS/system_model.py), [verify_extensions_saved.py](../scripts/verify_extensions_saved.py).

| Display | Stable paper label |
|---|---|
| Main Figure 9 | `fig:dispatch_request_realizability` |
| Table S25 | `tab:registered_system_settings` |
| Table S26 | `tab:sat_selected_counts` |
| Table S27 | `tab:sat_service_energy` |

Figure 9 separates economic from service selections. The representative +20.525393 kWh energy excess belongs to a service request. Among equal objective cases, the corresponding unrealizable selections are 0/10 for economic requests and 5/14 for primary service requests. These denominators differ from the full 26 assessments.

## Network support

Sources: [RTS_EXACT_CERTIFICATE_STATUS.csv](../extensions/rts/RTS_EXACT_CERTIFICATE_STATUS.csv), [FULL_NETWORK_NATIVE_ROW_REGISTER.csv](../extensions/source_layout/ECM_AUTONOMOUS_DEEP_RESEARCH_20261018/03_RTS_EXACT_NETWORK/FULL_NETWORK_NATIVE_ROW_REGISTER.csv), [NORMALIZED_RTS_INPUT.json](../extensions/source_layout/ECM_AUTONOMOUS_DEEP_RESEARCH_20261018/00_AUTHORITY_CONTROL/PREVIOUS_CORE/02_PROTOCOL/NORMALIZED_RTS_INPUT.json), [verify_rts_requests_saved.py](../scripts/verify_rts_requests_saved.py).

| Display | Stable paper label |
|---|---|
| Table S28 | `tab:rts_certificate_inputs` |

Table S28 concerns complete query set certificates. Original numerical requests and nearby exact feasible points are separately described in the [certificate guide](numerical_certificates.md).

## Operating states and data interfaces

Sources: [Simulation_Policy.json](../data/Simulation_Policy.json), [Source_Driven_Simulation.csv](../data/Source_Driven_Simulation.csv), [Simulation_Saved_States.jsonl](../data/Simulation_Saved_States.jsonl), [Measured_Window_Summaries.csv](../data/Measured_Window_Summaries.csv), [Operational_Source_Descriptions.json](../data/Operational_Source_Descriptions.json), [Elspotprices_DK1_2025_01.json](../external_data/energinet/Elspotprices_DK1_2025_01.json), [DATA_GUIDE.md](../DATA_GUIDE.md), [SOURCE_DEPENDENCY_GUIDE.md](../SOURCE_DEPENDENCY_GUIDE.md), [verify_saved_records.py](../verify_saved_records.py).

| Display | Stable paper label |
|---|---|
| Figure S4 | `fig:measured_coverage` |
| Table S20 | `tab:windows` |
| Table S21 | `tab:data_interfaces` |

## Check a display

Run the combined entry in the [quickstart](reviewer_quickstart.md), then locate the display by its stable label in the source map. The map identifies its input, implementation, certificate and reproduction scope. Conceptual figures use the linked definitions and proof sources rather than invented numerical inputs. Native graph editing is separate from these checks.
