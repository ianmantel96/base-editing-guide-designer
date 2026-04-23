# Base Editing Guide Designer

A local browser-based CRISPR base-editing guide and reagent design assistant.

The tool starts from a gene, species, and protein mutation; fetches reference context from Ensembl; helps choose ABE/CBE editor presets, PAM modes, guide sequences, reagent formats, and exports design files with BE-Designer cross-check support.

## How To Use

Open `index.html` in a browser. Chrome or Edge are recommended for the best file-saving support.

Typical workflow:

1. Enter gene, species, and protein mutation.
2. Run the reference lookup.
3. Confirm transcript, strand, codon, and intended edit.
4. Scan guides using NGG, NGN, or SpRY/relaxed PAM modes.
5. Select a guide and editor/reagent strategy.
6. Cross-check in BE-Designer.
7. Complete final checks.
8. Export the design bundle as a ZIP or folder.

## Outputs

The export bundle includes:

- design summary
- order sheet CSV
- guide FASTA
- Benchling-friendly GenBank context
- BE-Designer cross-check file
- project JSON record
- vendor/core inquiry text

## Important Caveats

This tool is a design assistant, not a replacement for experimental judgment.

Before ordering reagents, confirm:

- transcript and codon mapping
- gene strand and sequence orientation
- editor/PAM compatibility
- guide sequence excludes the PAM
- bystander edits
- reagent format and vendor/core availability
- BE-Designer or other independent cross-check

The tool does not currently perform genome-wide off-target analysis.

