# Data dictionary

CSV headers below are copied from the supplied files. Exact fractions are rational strings. A blank, unavailable, unresolved, empty, inapplicable or skipped value keeps its recorded meaning. The [data guide](../DATA_GUIDE.md) defines counting units; the [record dictionary](../Internal_Record_Dictionary.md) explains residuals and timing fields.

Power and energy units follow each instance. MW and MWh are distinct from kW and kWh. Column names are retained exactly, including historical abbreviations. The [original external column dictionary](../data/Original_External_Column_Dictionary.csv) gives 220 detailed field definitions.

## File index

| File | Rows | Columns |
|---|---:|---:|
| [Directional_Objective_Values.csv](../data/Directional_Objective_Values.csv) | 104 | 9 |
| [External_Assessments.csv](../data/External_Assessments.csv) | 3,772 | 22 |
| [External_Instances.csv](../data/External_Instances.csv) | 34 | 27 |
| [External_Transitions.csv](../data/External_Transitions.csv) | 4 | 20 |
| [Historical_Computational_Settings.csv](../data/Historical_Computational_Settings.csv) | 32 | 6 |
| [Internal_Assessments.csv](../data/Internal_Assessments.csv) | 936 | 60 |
| [Internal_Pairs.csv](../data/Internal_Pairs.csv) | 468 | 14 |
| [Lossless_Control_Factor_Lookup.csv](../data/Lossless_Control_Factor_Lookup.csv) | 312 | 12 |
| [Lossless_Figure_Cells.csv](../data/Lossless_Figure_Cells.csv) | 408 | 8 |
| [Measured_Window_Summaries.csv](../data/Measured_Window_Summaries.csv) | 9 | 18 |
| [Operational_Source_Screening.csv](../data/Operational_Source_Screening.csv) | 39 | 20 |
| [Original_External_Column_Dictionary.csv](../data/Original_External_Column_Dictionary.csv) | 220 | 5 |
| [Regression_Assessments.csv](../data/Regression_Assessments.csv) | 72 | 60 |
| [Repeated_Timing_Summaries.csv](../data/Repeated_Timing_Summaries.csv) | 108 | 17 |
| [Source_Driven_Simulation.csv](../data/Source_Driven_Simulation.csv) | 507 | 19 |
| [Source_Formulations.csv](../data/Source_Formulations.csv) | 59 | 21 |
| [Temporal_Query_Classifications.csv](../data/Temporal_Query_Classifications.csv) | 65 | 6 |
| [Timing_Repetition_Records.csv](../data/Timing_Repetition_Records.csv) | 648 | 21 |
| [Two_Interval_Control_Lookup.csv](../data/Two_Interval_Control_Lookup.csv) | 9 | 15 |

## data/Directional_Objective_Values.csv

`state_id`, `e0_MWh`, `direction_id`, `u`, `h_R_MW`, `h_X_MW`, `gap_MW`, `gap_kW`, `gap_exact_MW`.

## data/External_Assessments.csv

`case_id`, `anchor`, `family`, `initial_energy`, `energy_unit`, `domain_fraction`, `T`, `interval_h`, `role`, `classification`, `status`, `witness_count`, `mechanisms`, `SOC_admissible_failure_count`, `maximum_native_residual`, `residual_unit`, `model_parameter_hash`, `complete_model_state_hash`, `input_hash`, `result_sha256`, `independent_native_status`, `scope`.

## data/External_Instances.csv

`instance_id`, `anchor`, `family`, `mapping_status`, `source_sha256`, `equations`, `energy_unit`, `power_unit`, `lo`, `hi`, `charge_rating`, `discharge_rating`, `eta_charge`, `eta_discharge`, `T`, `interval_h`, `state_dimensions`, `dimension_count`, `query`, `coarse_points`, `extra_VDC`, `boundary_points`, `EQ`, `STRICT`, `model_parameter_hash`, `terminal`, `terminal_floor`.

## data/External_Transitions.csv

`transition_id`, `anchor`, `from_case`, `to_case`, `from_energy_MWh`, `to_energy_MWh`, `charge_MW`, `discharge_MW`, `duration_h`, `direction`, `action_native_feasible`, `SOC_feasible`, `source_parameters_unchanged`, `query_horizon`, `from_result_sha256`, `to_result_sha256`, `witness_row`, `max_witness_residual`, `severity_unit`, `scope`.

## data/Historical_Computational_Settings.csv

`setting`, `value_tex`, `unit`, `applicable_route`, `scientific_role`, `recorded_authority_type`.

## data/Internal_Assessments.csv

`case_id`, `paired_setting_id`, `phase`, `horizon_T`, `eta_c`, `eta_d`, `interval_duration`, `row_form`, `initial_rule`, `old_or_new_state`, `e0`, `effective_initial_energy`, `eligible`, `relaxed_nonempty`, `exact_status`, `EQ_CERTIFIED`, `STRICT_CERTIFIED`, `EMPTY_CERTIFIED`, `UNKNOWN`, `TIMEOUT`, `BUDGET_EXCEEDED`, `NOT_APPLICABLE`, `max_validity_test_value`, `max_validity_value_availability`, `checked_row_max_or_partial_lower_bound`, `max_SOC_valid_power_excess`, `SOC_power_value_availability`, `violating_row_family`, `violating_constraint_index`, `first_violating_period_if_defined`, `witness_available`, `witness_type`, `violation_magnitude`, `SOC_witness_status`, `SOC_pass_power_fail_smt`, `predicted_subproblem_count`, `actual_LP_calls`, `LP_time`, `SMT_time`, `full_sign_time`, `witness_verification_time`, `model_construction_time`, `transform_preprocessing_time`, `total_wall_time`, `peak_memory_if_available`, `input_hash`, `implementation_hash`, `solver_version`, `environment_hash`, `result_hash`, `process_status`, `old_status`, `new_status`, `status_transition`, `old_max_validity_test_value`, `new_max_validity_test_value`, `delta_validity_test_value`, `stale_validity_failure`, `SOC_admissibility_transition`, `SOC_transition_meaning`.

## data/Internal_Pairs.csv

`paired_setting_id`, `T`, `eta_c`, `h`, `row_form`, `initial_rule`, `e0`, `e1`, `old`, `new`, `first_action_feasible`, `SOC_admissible_witness`, `old_case_id`, `new_case_id`.

## data/Lossless_Control_Factor_Lookup.csv

`case_id`, `paired_setting_id`, `horizon_T`, `eta_c`, `eta_d`, `interval_duration`, `row_form`, `initial_rule`, `old_or_new_state`, `effective_initial_energy`, `eligible`, `exact_status`.

## data/Lossless_Figure_Cells.csv

`horizon`, `row_index`, `duration_h`, `row_form`, `initialization`, `state`, `status`, `case_id`.

## data/Measured_Window_Summaries.csv

`window`, `dataset`, `timestamps`, `unique_SOC_exact`, `unique_physical_state_tuples`, `unique_engineering_SOC_bins`, `engineering_bin_width_percentage_points`, `largest_exact_SOC_fraction`, `largest_engineering_bin_fraction`, `SOC_min`, `SOC_max`, `SOC_span_percentage_points`, `source_gap_free`, `native_model_complete`, `full_queries_evaluated`, `mapping_status`, `diversity_flag`, `frozen_before_outcomes`.

## data/Operational_Source_Screening.csv

`dataset_id`, `provider`, `URL`, `download_date`, `license_access`, `direct_BESS_telemetry`, `power`, `SOC`, `energy`, `capacity`, `resolution`, `duration`, `missing_fraction`, `units_documented`, `eligibility`, `exclusion_reason`, `stage2b_recheck`, `native_model_complete`, `full_query_evaluated`, `metadata_evidence`.

## data/Original_External_Column_Dictionary.csv

`file`, `column`, `meaning`, `unit`, `missing_policy`.

## data/Regression_Assessments.csv

`case_id`, `paired_setting_id`, `phase`, `horizon_T`, `eta_c`, `eta_d`, `interval_duration`, `row_form`, `initial_rule`, `old_or_new_state`, `e0`, `effective_initial_energy`, `eligible`, `relaxed_nonempty`, `exact_status`, `EQ_CERTIFIED`, `STRICT_CERTIFIED`, `EMPTY_CERTIFIED`, `UNKNOWN`, `TIMEOUT`, `BUDGET_EXCEEDED`, `NOT_APPLICABLE`, `max_validity_test_value`, `max_validity_value_availability`, `checked_row_max_or_partial_lower_bound`, `max_SOC_valid_power_excess`, `SOC_power_value_availability`, `violating_row_family`, `violating_constraint_index`, `first_violating_period_if_defined`, `witness_available`, `witness_type`, `violation_magnitude`, `SOC_witness_status`, `SOC_pass_power_fail_smt`, `predicted_subproblem_count`, `actual_LP_calls`, `LP_time`, `SMT_time`, `full_sign_time`, `witness_verification_time`, `model_construction_time`, `transform_preprocessing_time`, `total_wall_time`, `peak_memory_if_available`, `input_hash`, `implementation_hash`, `solver_version`, `environment_hash`, `result_hash`, `process_status`, `old_status`, `new_status`, `status_transition`, `old_max_validity_test_value`, `new_max_validity_test_value`, `delta_validity_test_value`, `stale_validity_failure`, `SOC_admissibility_transition`, `SOC_transition_meaning`.

## data/Repeated_Timing_Summaries.csv

`input_id`, `horizon_intervals`, `charging_efficiency`, `interval_duration_h`, `formulation`, `assessment_state`, `route`, `scheduled_repetitions`, `completed_repetitions`, `timeout_repetitions`, `skipped_repetitions`, `warmup_excluded`, `recorded_route_seconds`, `completed_only_minimum_s`, `completed_only_median_s`, `completed_only_maximum_s`, `completed_only_IQR_s`.

## data/Source_Driven_Simulation.csv

`window`, `index`, `timestamp_local`, `energy_kWh`, `SOC_fraction`, `charge_kW`, `discharge_kW`, `net_power_kW`, `next_energy_kWh`, `target_energy_kWh`, `endpoint`, `source_sha256`, `label`, `first_action_native_feasible`, `case_id`, `classification`, `complete_model_state_hash`, `result_sha256`, `full_query_T`.

## data/Source_Formulations.csv

`source_id`, `title`, `year`, `venue`, `DOI`, `DOI_status`, `formulation_family`, `affine`, `state_dependent`, `state_dependent_power_limits`, `efficiency_model`, `query_variables`, `complementarity`, `parameter_completeness`, `source_independence`, `already_used`, `eligible`, `reason`, `primary_url`, `audit_evidence`, `inherited_register_sha256`.

## data/Temporal_Query_Classifications.csv

`state_id`, `e0_MWh`, `query`, `classification`, `qualification`, `statistical_unit`.

## data/Timing_Repetition_Records.csv

`runtime_repeat_id`, `repeat_index`, `warmup`, `wall_time`, `cpu_time_if_available`, `CPU_note`, `LP_calls`, `SMT_status`, `memory_if_available`, `memory_scope`, `process_status`, `case_id`, `T`, `eta_c`, `h`, `row_form`, `state`, `route`, `input_hash`, `implementation_hash`, `environment_hash`.

## data/Two_Interval_Control_Lookup.csv

`case_id`, `eta_c`, `duration_min`, `initial_rule`, `row_form`, `old_e0_MWh`, `new_e0_MWh`, `numerical_lp_excess_MW`, `display_positive_part_kW`, `saved_SOC_pass_power_fail_smt`, `source_sha256`, `locator`, `transformation`, `statistical_unit`, `generalized_regression_case_id`.
