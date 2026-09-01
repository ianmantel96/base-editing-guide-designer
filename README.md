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

## Recommended installation

Because MUTATR is not notarized through the paid Apple Developer Program,
downloading GitHub's automatic ZIP can cause macOS or institutional security
software to quarantine the app launcher. Cloning the repository avoids the
GitHub ZIP issue and is the recommended installation method.

### Install with Codex or Claude

Open Codex or Claude Code on your Mac and paste the prompt below:

```text
Please install and test MUTATR on this Mac from:
https://github.com/ianmantel96/base-editing-guide-designer

Please do the following:
1. Confirm that this is a Mac and that Google Chrome is installed at
   /Applications/Google Chrome.app.
2. Clone the repository into ~/Applications/MUTATR. Create ~/Applications if
   needed. If that destination already exists, do not overwrite it; inspect it
   and update it safely instead.
3. Confirm that MUTATR.app and Backend are next to each other.
4. Confirm that MUTATR.app/Contents/MacOS/MUTATR is present and executable.
5. Launch MUTATR.app.
6. Allow the first-launch browser-helper setup to finish, then confirm that the
   MUTATR local app server and automation helper are healthy.
7. Tell me what you checked, what you changed, and whether MUTATR is ready.

Do not change MUTATR workflow logic, scientific settings, or source code.
```

### Install manually with Git

In Terminal, run:

```bash
mkdir -p "$HOME/Applications"
git clone https://github.com/ianmantel96/base-editing-guide-designer.git "$HOME/Applications/MUTATR"
open "$HOME/Applications/MUTATR/MUTATR.app"
```

Keep `MUTATR.app` and `Backend/` together. The first launch may take about a
minute while MUTATR prepares its browser helper.

### ZIP-download fallback

If you must use **Code -> Download ZIP**, unzip it but do not open MUTATR yet.
First remove the download quarantine from the entire unzipped folder:

1. Open Terminal.
2. Type `xattr -dr com.apple.quarantine `, including the trailing space.
3. Drag the entire unzipped folder into Terminal.
4. Press Return.
5. Right-click `MUTATR.app` and choose **Open**.

If the executable has already been removed, delete that download and start
again. On an institution-managed Mac, local security software may still require
your IT department to allow MUTATR.

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
