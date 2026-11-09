# State, residual and timing fields

This dictionary defines the controlled study records. The [data guide](DATA_GUIDE.md) provides file counts and the [CSV dictionary](docs/data_dictionary.md) lists exact column names. Field names below retain their original spelling.

## Identity and status

| Field or status | Meaning |
|---|---|
| `case_id` | Identifies one fixed model and state |
| `paired_setting_id` | Links the states before and after a predefined update |
| `horizon_T` | Number of intervals |
| `interval_duration` | Interval duration in rational hours |
| `e0`, `effective_initial_energy` | Stored energy in MWh |
| `eta`, `rho` | Dimensionless efficiency and retention coefficients |
| `EQ`, `STRICT`, `EMPTY` | Equal query sets, strict inclusion and an empty relaxed set, respectively; each requires its stated certificate |
| `TIMEOUT`, `UNKNOWN`, `ERROR` | Unfinished or unsuccessful computational outcomes |
| `NOT_APPLICABLE` | A state slot excluded by the initialization or update design |
| `SKIPPED` | A route intentionally not executed |

A decided state may still have an unresolved route. Route R3 was deliberately skipped beyond eight intervals. Regression slots, repeated timings and solver calls are separate from the state assessment denominator. The design is not a random sample of battery operating conditions.

## Residuals and witnesses

State of charge (SOC) admissibility fields describe the retained witness and its reconstructed energy bounds.

| Field | Interpretation |
|---|---|
| `max_validity_test_value` | A lifted target maximum when fully obtained, or when a completed positive critical row maximum dominates automatically preserved rows |
| `max_validity_value_availability` | Indicates whether the value is complete, partial or unavailable; a blank is not zero |
| `checked_row_max_or_partial_lower_bound` | A partial solver best is a lower bound, not a completed optimum |
| `max_SOC_valid_power_excess` | Existing endpoint in MW, computed by full sign enumeration where permitted and completed |
| `violation_magnitude` | Raw maximum residual among violating native rows; not necessarily optimized or normalized |
| `period` | Interval index starting at zero |
| `SOC_admissibility_transition` | A property of the saved witness, not every admissible query |
| `NO_CERTIFIED_WITNESS` | No certified witness is recorded; it does not imply SOC admissibility |

Skipped automatically preserved rows do not justify a negative interior distance. Native residuals retain their individual energy or power units. At larger horizons, exact existence results and saved witnesses remain available even where full sign optimization was not completed. No residual is interpreted as a probability or risk score.

## Timings and identities

| Quantity | Definition |
|---|---|
| Wall times | Seconds; model construction, transformation, route and whole state scopes are separate |
| Peak memory | State process working set peak in bytes |
| Central processing unit (CPU) time | State CPU time is saved separately; route CPU time was not measured |
| Warmup index zero | Excluded from repeated timing summaries |
| Repeat indices one to five | All retained, including timeouts |
| Completed only medians | Computed from completed repeats and labeled accordingly |
| `result_hash` | Identity of the immutable result JSON; not a recursive self hash |
| Implementation and environment hashes | Refer to the retained manifests |

Counts retain inapplicable and skipped entries in their respective denominators. Timing records do not establish solver superiority or real time performance. The files contain no inferred confidence intervals, population failure rates or interpolated state classifications.
