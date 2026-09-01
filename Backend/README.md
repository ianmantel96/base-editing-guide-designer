# MUTATR

MUTATR is a local mutation research and CRISPR design workbench. It supports:

- mutation dossiers and literature search
- base editing
- prime editing
- nuclease disruption / indel design
- paired-guide deletion planning
- external browser checks for BE-Designer, pegFinder, and CHOPCHOP

## Recommended Launch

Use the launcher instead of opening HTML files directly.

### One-click launch

- Keep `MUTATR.app` and `Backend/` next to each other.
- Double-click `MUTATR.app`.

That starts:

- the local MUTATR app server on `http://127.0.0.1:8765` or the next free local port
- the local browser-automation helper on `http://127.0.0.1:8766`

The first launch creates a private Python environment in `Backend/.venv-browser`
and installs the browser helper. This requires internet access and may take about
a minute. Later launches reuse that environment.

### Terminal launch

```bash
python3 mutatr_runner.py start
```

To stop the local services:

```bash
python3 mutatr_runner.py stop
```

Or use the hidden stop script if you need to shut the local services down manually.

## Runtime Health

Open **Settings** inside MUTATR to see:

- whether the local app server is running
- whether the automation helper is running
- whether browser checks should work

If automation is down, Settings includes a **Restart Automation Helper** button.

## Typical Workflow

1. Create a mutation dossier in `mutatr.html`.
2. Explore literature with Europe PMC-backed search and optional AI summaries.
3. Open the CRISPR design workflow for:
   - base editing
   - prime editing
   - nuclease disruption / indel
   - paired-guide deletion
4. Use the browser-check steps for:
   - BE-Designer
   - pegFinder
   - CHOPCHOP
5. Export design files and workbook outputs.

## Important Caveats

MUTATR is a design assistant, not a replacement for experimental judgment.

Before ordering reagents, confirm:

- transcript and target mapping
- strand/orientation
- editor or nuclease compatibility
- guide architecture and delivery format
- bystander edits for base editing
- pegRNA strategy for prime editing
- independent cross-check results

MUTATR does not currently perform genome-wide off-target analysis.
