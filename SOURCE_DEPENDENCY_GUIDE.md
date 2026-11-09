# Source dependencies

The saved evidence checks use the files in this archive and the Python standard library. See the [environment guide](ENVIRONMENT.md) for package versions and the [optional rerun guide](docs/optional_full_research_rerun.md) for solver entry points.

| Input family | Available here | Further information |
|---|---|---|
| Author models and results | Implementations, fixed inputs, certificates and derived records | [Data guide](DATA_GUIDE.md) |
| Public price and system inputs | Energinet January 2025 DK1 response with 744 rows; selected PyPSA and network input files | [External data access](docs/external_data_access.md) |
| Operational measurements | Nine window summaries; raw trajectories and derived measurement plot remain external | [Source notices](THIRD_PARTY_NOTICES.md) |
| Literature | Source locators, equations and parameter mappings; publisher articles remain external | [Mapping records](data/Source_Mapping_Details.json) |

The 507 simulated timestamps and 86 model states are retained alongside the actual Energinet input. They are distinct from measured physical state tuples.
