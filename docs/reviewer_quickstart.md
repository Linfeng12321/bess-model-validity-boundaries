# Reader quickstart

Use this page to connect the paper to its implementations and check the supplied evidence.

## Run the saved evidence checks

Extract the complete archive into a new directory. Open a terminal at its root and use Python 3.12. The command requires only the standard library and no external data download.

```console
python -B scripts/verify_release.py --report-dir reports
```

The combined result is `reports/RELEASE_VERIFICATION.json`. A successful check reports `status: PASS`; each component also writes a separate report. [Environment details](../ENVIRONMENT.md) distinguish these checks from optional solver dependencies.

| Reader action | Starting point | What it establishes |
|---|---|---|
| Inspect | [Paper source map](main_sm_code_data_crosswalk.md) | Connections between 192 scientific objects and their sources |
| Verify saved records | Command above and [certificate guide](numerical_certificates.md) | Arithmetic, native constraint checks and agreement with fixed summaries |
| Optional research rerun | [Research source entries](optional_full_research_rerun.md) | The implementations and environments needed for a separately configured solver run |

## Read the reports

| Report in `reports/` | Content |
|---|---|
| `RELEASE_VERIFICATION.json` | Combined status, file manifest and fixed expectations |
| `canonical.json` | Device witnesses, mapped literature states, query controls and descriptive summaries |
| `extensions_saved_verification.json` | Later exact certificates and extension records |
| `rts_request_evidence_verification.json` | Separate network set certificates, numerical requests and nearby points |
| `display_summary.json`, `system_saved.json` | Fixed display counts and selected system requests |

The report directory is new output. The supplied research records remain unchanged.

## Find a paper result

The [figure and table index](figures_and_tables.md) groups displays by research question. Figure 8 concerns temporal queries and directional objectives. Figure 9 concerns selected economic and service requests. Supplementary Material (SM) Sections S10, S11 and S12 contain later horizon certification, three bus dispatch and network evidence, respectively.

Use the [data guide](../DATA_GUIDE.md) for counts and units, the [field dictionary](data_dictionary.md) for columns and the [code guide](code_provenance.md) for implementation locations. The [model scope](study_scope_and_model_assumptions.md) explains the guarantees attached to each evidence type.
