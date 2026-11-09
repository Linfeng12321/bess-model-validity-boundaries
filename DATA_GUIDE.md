# Research data guide

The records connect fixed model inputs to classifications, witnesses and paper results. Exact fraction strings, scientific values and vector order are retained. The [field dictionary](docs/data_dictionary.md) lists CSV columns; the [record dictionary](Internal_Record_Dictionary.md) defines residual and timing semantics. Supplementary Material (SM) section references follow the supplied paper source map.

## Controlled states and horizons

| File | Counting unit | Content and connection |
|---|---|---|
| [Internal_Assessments.csv](data/Internal_Assessments.csv) | 936 state slots | Original classifications, route availability and times; SM S3–S4 |
| [Internal_Pairs.csv](data/Internal_Pairs.csv) | 468 predefined pairs | Before and after links, eligibility and fixed parameters |
| [Internal_Saved_States.jsonl](data/Internal_Saved_States.jsonl) | 936 input and result objects | Native inputs, route records and rational witnesses |
| [Regression_Assessments.csv](data/Regression_Assessments.csv) | 72 regression slots | Implementation compatibility checks, separate from the 936 slots |
| [Boundary_Grid_Checks.json](data/Boundary_Grid_Checks.json) | 330 discrete checks | Fixed formulation and parameter combinations; SM S2 |
| [Boundary_Quantified_Results.json](data/Boundary_Quantified_Results.json) | 12 exact domain decisions | Preserved quantified outcomes with [declared obligations](data/Boundary_Check_Specification.json) |
| [Exact_Hull_Constructions.json](data/Exact_Hull_Constructions.json) | 9 constructions | Feasible endpoints, midpoints, exclusive reconstruction and native residuals; SM S5 |

The original 936 slots comprise 277 equal query sets (EQ), 331 strict inclusion (STRICT), 152 unresolved and 176 inapplicable assessments. Later certificates concern the same 152 inputs. [Version accounting](extensions/certification/) gives the cumulative 426 EQ and 334 STRICT, with 82 EQ to STRICT changes among the same 468 pairs. The 330 grid checks and the 12 quantified domain decisions are separate evidence; interpolation is not a continuous boundary proof.

## Literature mappings

| File | Counting unit | Content and connection |
|---|---|---|
| [External_Instances.csv](data/External_Instances.csv) | 34 mapped instances from ten sources | Ratings, efficiencies, horizon, units and terminal rule; SM S7 |
| [External_Assessments.csv](data/External_Assessments.csv) | 3,772 instance and state assessments | 113 EQ and 3,659 STRICT |
| [External_Saved_States.jsonl](data/External_Saved_States.jsonl) | 3,772 input and result pairs | Exact saved vectors and complete mapped parameters |
| [External_Transitions.csv](data/External_Transitions.csv) | 4 feasible updates | Two EQ to STRICT and two reverse transitions |
| [Source_Formulations.csv](data/Source_Formulations.csv) | 59 screening records | Source identity and eligibility |
| [Source_Mapping_Details.json](data/Source_Mapping_Details.json) | 83 expanded screening and mapping rows | Equations, transformations, retained constraints, exclusions and missing fields |

All 3,659 retained strict inclusion witnesses violate stored energy bounds. Of these, 329 also violate retained native power constraints; 3,330 violate energy bounds only. These categories describe retained witnesses, not every possible violating query.

The 59 screening records and 83 expanded rows are not additional evaluated sources or devices. [Source descriptions](data/Source_Screening_Descriptions.json), [device descriptions](data/Device_Mapping_Descriptions.json) and [operational descriptions](data/Operational_Source_Descriptions.json) retain 59, 34 and 39 records, respectively. Their `field_tex` and `value_tex` entries preserve source LaTeX. Join device descriptions by anchor names rather than legacy display ordinals. Final outcomes are in the numerical masters and saved states.

## Queries and computation times

| File | Counting unit | Content and connection |
|---|---|---|
| [Temporal_Query_Classifications.csv](data/Temporal_Query_Classifications.csv) | 65 records: 13 energies and 5 queries | Complete and projected query relations; SM S6 |
| [Directional_Objective_Values.csv](data/Directional_Objective_Values.csv) | 104 records: 13 energies and 8 directions | Exact values, including 24 displayed comparisons |
| [Two_Interval_Control_Lookup.csv](data/Two_Interval_Control_Lookup.csv) and [records](data/Two_Interval_Control_Records.json) | 9 controls | Updated energy, numerical linear programming (LP) excess and separate logical outcomes |
| [Timing_Repetition_Records.csv](data/Timing_Repetition_Records.csv) | 648 route records, including warmups | Repeat indicators and time scopes; SM S4 |
| [Repeated_Timing_Summaries.csv](data/Repeated_Timing_Summaries.csv) | 108 input and route summaries | 540 scheduled repeats: 365 complete, 55 timeouts and 120 skipped |
| [Historical_Computational_Settings.csv](data/Historical_Computational_Settings.csv) | 32 setting entries | Earlier route contexts, including an unavailable historical HiGHS version |
| [Lossless_Control_Factor_Lookup.csv](data/Lossless_Control_Factor_Lookup.csv) | 312 original assessments | Charging efficiency one: 144 EQ, 104 unresolved timeouts and 64 inapplicable |
| [Lossless_Figure_Cells.csv](data/Lossless_Figure_Cells.csv) | 408 display combinations | Includes combinations outside the study design |

The nine controls join to the regression records by generalized case identifier. They are separate from the 936 slot study. Warmup index zero is excluded from repeated summaries; repetitions one to five retain timeout records. Figure dashes denote combinations outside the design. Later certification does not rewrite the original timing or lossless factor records. The later environment is not assigned retrospectively to earlier settings.

## Simulated and measured operating states

| File | Counting unit | Definition |
|---|---|---|
| [Source_Driven_Simulation.csv](data/Source_Driven_Simulation.csv) | 507 timestamp rows | State and action records from a price driven simulation |
| [Simulation_Saved_States.jsonl](data/Simulation_Saved_States.jsonl) | 86 distinct complete model states | Four interval inputs and saved STRICT witnesses |
| [Simulation_Policy.json](data/Simulation_Policy.json) | One recorded policy | Calibration, target rule, window selection and device parameters |
| [Energinet price response](external_data/energinet/Elspotprices_DK1_2025_01.json) | 744 source rows | Actual frozen January 2025 DK1 input |
| [Measured_Window_Summaries.csv](data/Measured_Window_Summaries.csv) | 9 measured windows | 14,121 timestamps and 7,729 physical state tuples |
| [Operational_Source_Screening.csv](data/Operational_Source_Screening.csv) | 39 source and metadata candidates | Access and model eligibility information |

Physical tuples use dataset, device, state of charge (SOC) and available SOC limits. They do not include power or a complete native model state. The measured windows describe visited conditions and carry no complete query set certificates.

The exported simulation CSV withholds its provider `price_EUR_MWh` column, while retaining all 507 action rows and 86 model state identifiers. The separate unchanged price JSON is included. `Source_Price_Inputs.json` is a historical alias, not an additional runtime dependency. [External data access](docs/external_data_access.md) explains source versions and permissions.

## Units, missing values and file identities

Power and energy use each instance's paired source units: MW and MWh, or kW and kWh. Constraint residuals retain their row units and scaling. A headroom residual is not automatically a delivered power excess. Empty, unresolved, inapplicable, unassessable and skipped records have distinct meanings. An unavailable value is not zero; a skipped route time is not a measured duration.

The portable builders [internal_model.py](code/internal_model.py) and [external_mapping.py](code/external_mapping.py) support the saved record checks. The external builder uses `Fraction` in place of its common import. The recorded terminal adapter supplies the fixed terminal floor for the two building instances. Versioned implementations and their import names remain under [original_layout](code/original_layout/).

Hashes inside records identify original input or result serialization. Exported records with local paths removed have separate file identities in the [release manifest](release_manifest/SHA256SUMS.csv). The [certificate guide](docs/numerical_certificates.md) distinguishes arithmetic checks from preserved logical outcomes. [System extension records](extensions/README.md) cover three bus dispatch and network certificates.
