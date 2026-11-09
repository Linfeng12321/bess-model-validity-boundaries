# External data access

## Included upstream inputs

| Source | Included material and revision | Attribution and use |
|---|---|---|
| [Energinet Energy Data Service](https://www.energidataservice.dk/terms-and-conditions) | [January 2025 DK1 response](../external_data/energinet/Elspotprices_DK1_2025_01.json), 744 rows | Unchanged provider response under CC BY 4.0; [notice](../notices/Energinet_CC_BY_4_0.md) |
| [PyPSA Contributors](https://github.com/PyPSA/PyPSA/tree/23e243654c5657d8da3689d6baf5a03f3f3b455e) | [Three example inputs](../external_data/pypsa/) at the linked revision | CSV and notebook terms follow the [pinned REUSE record](../notices/PyPSA_REUSE.toml); software MIT terms are separate |
| [Reliability Test System of the Grid Modernization Laboratory Consortium (RTS-GMLC)](https://github.com/GridMod/RTS-GMLC/tree/3ece0d3725c844056132393ee252b3083dd4eab4) | [Ten source inputs and upstream README](../external_data/rts_gmlc/) at the linked revision | Preserve the DOE/NREL/ALLIANCE credit and [complete data notice](../external_data/rts_gmlc/README.md); no endorsement |

The Energinet response retains SHA256 `9da54c4e2b45bd8d780e3fdc23100d0b0151316a4d814eb9e483984c843725b7`. Other input identities are in the [release manifest](../release_manifest/SHA256SUMS.csv).

The three bus network extensions, storage parameters and service conditions are researcher specified assumptions. The PyPSA notebook credits Kyri Baker's illustrative three bus example. These inputs are not field validation. The network study maps public source data to the continuous model described in the [study scope](study_scope_and_model_assumptions.md).

The pinned RTS-GMLC notice ends abruptly in the upstream file. It is retained verbatim, without completing its text or relabeling it as MIT or CC BY. The upstream notice expressly permits copying and distribution provided the entire notice is retained. This release preserves that entire upstream file and credits DOE/NREL/ALLIANCE; it does not amend the truncated text or substitute MIT terms.

## Measurement and literature access

| Source | Available here | Separate access |
|---|---|---|
| [ACEN operational data](https://acenrenewables.com.au/new-england-bess-operational-data/) | Reported window summaries and source descriptions | Raw trajectories, derived measured plot data and Figure S4 native graph |
| [EPRI](https://msites.epri.com/period) | Reported window summaries and source descriptions | Raw trajectories and derived measured assets; applicable permissions remain unresolved |
| Primary literature | [Source equations and parameter mappings](../data/Source_Mapping_Details.json) and [paper source map](main_sm_code_data_crosswalk.md) | Publisher articles and the cited Rosewater source |

The nine measured window summaries span both providers. Web access does not establish redistribution permission. Their physical state tuples remain distinct from complete simulated model states; eligibility for model certification is explained in the [study scope](study_scope_and_model_assumptions.md).

[Third party notices](../THIRD_PARTY_NOTICES.md) retain the separate source conditions. [License information](../LICENSE_INFORMATION.md) addresses the author code and results.
