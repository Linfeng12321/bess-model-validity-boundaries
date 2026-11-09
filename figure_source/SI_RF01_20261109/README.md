# Original lossless control outcomes

This is Figure S2 of the Supplementary Information, with grouped display labels. It is not the Main Figure 4 transition matrix. The 24 paired rows and 17 horizons preserve all 312 original assessments: 144 EQ, 104 unresolved and 64 inapplicable. The other 96 display positions are outside the prescribed design. Later certifications have not been substituted.

Open `SI_RF01_GROUPED.opju` in Origin 2026 to edit the three native symbol plots, two native layers and grouped text. All five nonempty source worksheets are embedded; no screenshot is used as plot data. `SI_RF01_GROUPED.pdf` contains vector text and geometry with embedded Times New Roman fonts, no bitmap images. The PNG was rendered at 6693 × 5652 pixels for the 170 mm SM insertion width (about 1000 dpi). The SVG is an additional vector export. Normal PDF text is 7.92 pt at this width, headings/legend 8.40 pt.

`DISPLAY_CELL_MAP.csv` joins every cell to the unchanged machine fields and case ID. `source/horizon_states.csv` is a byte-identical frozen source copy. Historical source paths in that CSV are provenance, not required runtime inputs.

To replay the label-only patch, use Python with the `originpro` package and a licensed Origin 2026 installation on Windows:

```console
python patch_labels.py --output NEW_EMPTY_DIRECTORY
```

The output directory must not exist. The script opens `source/SI_RF01_INPUT.opju` in a new owned Origin process, edits presentation objects, saves and reopens the result, and checks all worksheet values. It does not classify states, solve models, or download data. Export raster DPI metadata is descriptive; native SVG/PDF retain editable geometry. This display script is separate from the 70 inherited scientific and verification Python files.
