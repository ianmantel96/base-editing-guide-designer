# MUTATR

MUTATR is a local mutation research and CRISPR design workbench for macOS.

It supports:

- mutation dossiers and literature search
- base editing
- prime editing
- nuclease disruption / indel design
- paired-guide deletion planning
- external browser checks for BE-Designer, pegFinder, and CHOPCHOP
- export of design summaries, order sheets, validation candidates, and workbooks

## macOS only

This packaged version of MUTATR is currently intended for **macOS** users.
The included app launcher supports both Apple-silicon and Intel Macs.

The folder should stay structured like this:

- `MUTATR.app`
- `Backend/`

`MUTATR.app` expects `Backend/` to remain next to it in the same folder.

## Quick start

1. Download or clone the `MUTATR` folder.
2. Keep `MUTATR.app` and `Backend/` together.
3. Make sure **Google Chrome** is installed in `/Applications`.
4. Open `MUTATR.app`.

On first launch, macOS may block the app because it is not notarized. If that happens:

1. Right-click `MUTATR.app`
2. Click `Open`
3. Confirm `Open`

If macOS still blocks it, go to:

- `System Settings -> Privacy & Security`

and allow the app to open.

## What MUTATR needs on your Mac

For this current version, MUTATR assumes:

- macOS
- Google Chrome installed in `/Applications/Google Chrome.app`
- Python 3 available at `/usr/bin/python3`
- internet access during the first launch so MUTATR can install its small browser-automation helper

The first launch may take a minute while that helper is prepared. Later launches
reuse the local helper and do not reinstall it. This version is packaged for easy
lab sharing, but it is still a local research tool rather than a fully notarized
consumer app.

## OpenAI API key

Some MUTATR features use OpenAI, but **your own API key is required**.

Examples of features that may use an OpenAI key:

- AI-assisted literature search or query expansion
- some live Addgene enrichment/search behavior

Core local CRISPR design and most exports do **not** require an OpenAI key.

Important:

- this repository should **not** be shared with a personal OpenAI API key inside it
- every user should add **their own** key on their own machine
- the key should be entered in **MUTATR Settings**

How to add your own key in MUTATR:

1. Open `MUTATR.app`
2. Open the **Settings** page inside MUTATR
3. Find the **OpenAI Settings** section
4. Paste your own OpenAI API key
5. Save the settings

How to get an OpenAI API key:

1. Create or sign into your OpenAI account
2. Go to the OpenAI platform API keys page
3. Create a new secret key
4. Copy it and paste it into MUTATR Settings on your Mac

If you do not add a key:

- MUTATR can still run
- but AI-assisted features will be limited or unavailable

## Manual troubleshooting

If `MUTATR.app` opens but browser automation features do not work:

1. Confirm Chrome is installed in `/Applications`
2. Confirm `Backend/` is still next to `MUTATR.app`
3. Close MUTATR completely
4. Re-open `MUTATR.app`

If the app opens but looks blank or stuck:

1. Quit `MUTATR.app`
2. Re-open it
3. If needed, open **Settings** inside MUTATR and check runtime/automation status

## Optional Codex setup prompt

If you use Codex and want it to prepare your Mac to run MUTATR, you can paste this prompt:

```text
Please help me verify that MUTATR is set up correctly on this Mac.

The MUTATR folder is here:
[replace this line with the path to your downloaded MUTATR folder]

Please do the following:
1. Confirm that `MUTATR.app` and `Backend/` are both present and still next to each other.
2. Confirm that Google Chrome exists at `/Applications/Google Chrome.app`.
3. Check whether the local MUTATR runtime files look intact.
4. Launch MUTATR from `MUTATR.app`.
5. Confirm that the local app server and automation helper are healthy.
6. If something obvious is missing or misconfigured, fix it if the fix is straightforward and safe.
7. Then tell me exactly what you checked, what you changed if anything, and whether MUTATR is ready to use.

Do not change any MUTATR workflow logic or scientific settings unless I explicitly ask.
```

## Typical workflow

1. Open or create a mutation dossier.
2. Review literature and mutation context.
3. Choose a CRISPR strategy:
   - base editing
   - prime editing
   - nuclease disruption / indel
   - paired-guide deletion
4. Review guides and external cross-checks.
5. Review editor or disruption plan.
6. Export design outputs.
7. Review validation candidates:
   - TaqMan validation
   - Sanger validation

## Scientific caveats

MUTATR is a design assistant, not a replacement for experimental judgment.

Before ordering or using reagents, confirm:

- transcript and target mapping
- strand/orientation
- editor or nuclease compatibility
- guide architecture and delivery format
- bystander edits for base editing
- pegRNA strategy for prime editing
- validation primers/probes in external tools
- independent cross-check results

MUTATR does **not** currently replace:

- genome-wide off-target analysis
- full assay specificity review
- wet-lab validation
- final experimental judgment
