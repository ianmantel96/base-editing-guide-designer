#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from pyppeteer import launch


HOST = "127.0.0.1"
PORT = 8766
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHOPCHOP_URL = "https://chopchop.cbu.uib.no/"


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8"))


def clean_seq(seq: str) -> str:
    return re.sub(r"[^ACGTacgt]", "", seq or "").upper()


def revcomp(seq: str) -> str:
    return clean_seq(seq).translate(str.maketrans("ACGT", "TGCA"))[::-1]


def unique_preserving(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = clean_seq(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def candidate_guides_from_target(text: str) -> list[str]:
    seq = clean_seq(text or "")
    if not seq:
        return []
    candidates: list[str] = []
    if len(seq) >= 20:
        candidates.extend([seq[:20], seq[-20:]])
    if len(seq) >= 23:
        candidates.extend([seq[:20], seq[1:21], seq[3:23]])
    return [item for item in unique_preserving(candidates) if len(item) == 20]


def parse_bedesigner_match(raw_text: str, tables: list[dict], selected_guide: str) -> dict | None:
    ordered = clean_seq(selected_guide)
    if not ordered:
        return None
    target_strand = revcomp(ordered)

    def is_match(target_text: str) -> tuple[bool, str, str]:
        seq = clean_seq(target_text or "")
        candidates = candidate_guides_from_target(seq)
        if ordered and ordered in seq:
            return True, ordered, "ordered_guide"
        if target_strand and target_strand in seq:
            return True, target_strand, "target_strand_reverse_complement"
        if ordered in candidates:
            return True, ordered, "ordered_guide"
        if target_strand in candidates:
            return True, target_strand, "target_strand_reverse_complement"
        return False, "", ""

    for table in tables or []:
        headers = [str(h or "").strip().lower() for h in table.get("headers", [])]
        for row in table.get("rows", []) or []:
            target_cell = next((cell for cell in row if re.search(r"[ACGT]{20,}", str(cell or ""), re.I)), "")
            matched, matched_guide, match_mode = is_match(str(target_cell or ""))
            if not matched:
                continue

            def pick(patterns: list[str]) -> str:
                for i, header in enumerate(headers):
                    if any(re.search(pattern, header, re.I) for pattern in patterns):
                        return str(row[i] or "") if i < len(row) else ""
                return ""

            return {
                "found": True,
                "matchedGuide": matched_guide,
                "matchMode": match_mode,
                "position": pick([r"position"]),
                "direction": pick([r"direction", r"strand"]),
                "gc": pick([r"\bgc\b"]),
                "editingWindowSequence": pick([r"editing.*window", r"window.*sequence", r"^sequence$"]),
            }

    compact = re.sub(r"\s+", " ", raw_text or "").strip()
    row_regex = re.compile(r"([ACGT]{20,25})\s+([ACGT]{3,10})\s+[A-Z\s]{1,40}\s+(\d+)\s+([+-])\s+(\d+(?:\.\d+)?)", re.I)
    for match in row_regex.finditer(compact):
        target_with_pam = match.group(1) or ""
        matched, matched_guide, match_mode = is_match(target_with_pam)
        if not matched:
            continue
        return {
            "found": True,
            "matchedGuide": matched_guide,
            "matchMode": match_mode,
            "position": match.group(3) or "",
            "direction": match.group(4) or "",
            "gc": match.group(5) or "",
            "editingWindowSequence": match.group(2) or "",
        }
    return None


def chopchop_candidate_guides(target_sequence: str, pam_len: int = 3) -> list[str]:
    seq = clean_seq(target_sequence)
    if not seq:
        return []
    candidates = [seq, revcomp(seq)]
    if len(seq) > pam_len:
        candidates.extend([seq[:-pam_len], seq[pam_len:], revcomp(seq[:-pam_len]), revcomp(seq[pam_len:])])
    if len(seq) >= 20:
        candidates.extend([seq[:20], seq[-20:], revcomp(seq[:20]), revcomp(seq[-20:])])
    return [item for item in unique_preserving(candidates) if len(item) >= 20]


async def browser_page():
    browser = await launch(
        headless=True,
        args=["--no-sandbox"],
        executablePath=CHROME_PATH,
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
    )
    page = await browser.newPage()
    return browser, page


def parse_pegfinder_text(text: str) -> dict:
    def grab(pattern: str) -> str:
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1).strip() if m else ""

    recommended = {
        "spacer": grab(r"Recommended selections for pegRNA design\s+sgRNA:\s*([ACGT]+)"),
        "rtt": grab(r"RT template \((?:\d+)\s*nt\):\s*([ACGT]+)"),
        "pbs": grab(r"PBS \((?:\d+)\s*nt\):\s*([ACGT]+)"),
        "pe3_nick": grab(r"PE3 nicking sgRNA:\s*([A-Za-z0-9]+)"),
        "full_pegRNA": grab(r"Full-length pegRNA:\s*([A-Za-z0-9]+)")
    }
    incompatible_message = ""
    if "Preselected sgRNA is incompatible with desired edit" in text:
        incompatible_message = "Preselected sgRNA is incompatible with desired edit."
    return {
        "recommended": recommended,
        "preselected_incompatible": bool(incompatible_message),
        "message": incompatible_message,
    }


async def automate_pegfinder(payload: dict) -> dict:
    wildtype = clean_seq(payload.get("wildtype", ""))
    edited = clean_seq(payload.get("edited", ""))
    enzyme = payload.get("enzyme", "Cas9-NGG")
    preselected = clean_seq(payload.get("preselected_sgrna", ""))
    min_nick = str(payload.get("minNickDist", 40))
    max_nick = str(payload.get("maxNickDist", 150))

    if not wildtype or not edited:
        raise ValueError("wildtype and edited sequences are required")

    async def run_once(use_preselected: bool) -> dict:
        browser, page = await browser_page()
        try:
            await page.goto("http://pegfinder.sidichenlab.org/", {"waitUntil": "networkidle2", "timeout": 30000})
            await page.type('textarea[name="wildtype"]', wildtype)
            await page.type('textarea[name="edited"]', edited)
            await page.click('input[name="PE3cb"][value="1"]')
            await page.evaluate(
                """(enzyme, minNick, maxNick, preselected, usePreselected) => {
                    document.querySelector('select[name="enzyme"]').value = enzyme;
                    document.querySelector('input[name="minNickDist"]').value = minNick;
                    document.querySelector('input[name="maxNickDist"]').value = maxNick;
                    if (usePreselected && preselected) {
                      document.querySelector('input[name="c_sgRNA"]').value = preselected;
                    }
                }""",
                enzyme,
                min_nick,
                max_nick,
                preselected,
                use_preselected,
            )
            await page.evaluate('document.forms[0].submit()')
            await page.waitForNavigation({"waitUntil": "networkidle2", "timeout": 30000})
            text = await page.evaluate("document.body.innerText")
            return {
                "url": page.url,
                "raw_text": text,
                **parse_pegfinder_text(text),
            }
        finally:
            await browser.close()

    first = await run_once(bool(preselected))
    if first.get("preselected_incompatible") and preselected:
        fallback = await run_once(False)
        fallback["fallback_used"] = True
        fallback["preselected_attempted"] = preselected
        return fallback
    first["fallback_used"] = False
    first["preselected_attempted"] = preselected
    return first


def be_pam_id(mode: str) -> str:
    mode = (mode or "NGG").upper()
    if mode == "NRY":
        return "18"
    if mode == "NRNH":
        return "23"
    if mode == "NRCH":
        return "25"
    if mode == "NGN":
        return "17"
    if mode == "NNN":
        return "18"
    return "1"


def _matches_family(seq: str, family: str) -> bool:
    seq = clean_seq(seq)
    family = (family or "").upper()
    if not seq or not family or len(seq) != len(family):
        return False
    codes = {
        "A": {"A"},
        "C": {"C"},
        "G": {"G"},
        "T": {"T"},
        "N": {"A", "C", "G", "T"},
        "R": {"A", "G"},
        "Y": {"C", "T"},
        "H": {"A", "C", "T"},
    }
    return all(base in codes.get(code, set()) for base, code in zip(seq, family))


def bedesigner_mode_candidates(sequence: str, selected_guide: str, fallback_mode: str) -> list[str]:
    seq = clean_seq(sequence)
    ordered = clean_seq(selected_guide)
    if not seq or not ordered:
        return [(fallback_mode or "NGG").upper()]

    target = ordered if ordered in seq else ""
    strand = "+"
    if not target:
        rc = revcomp(ordered)
        if rc in seq:
            target = rc
            strand = "-"
    if not target:
        return [(fallback_mode or "NGG").upper()]

    idx = seq.find(target)
    upstream = seq[max(0, idx - 4):idx]
    downstream = seq[idx + len(target):idx + len(target) + 4]

    if strand == "+":
        target_pam2 = downstream[:2]
        target_pam3 = downstream[:3]
        target_pam4 = downstream[:4]
    else:
        target_pam2 = upstream[-2:]
        target_pam3 = upstream[-3:]
        target_pam4 = upstream[-4:]

    oriented = [
        target_pam2,
        target_pam3,
        target_pam4,
        revcomp(target_pam2),
        revcomp(target_pam3),
        revcomp(target_pam4),
    ]

    candidates: list[str] = []
    if any(_matches_family(item, "NGG") for item in oriented if len(item) == 3):
        candidates.append("NGG")
    if any(_matches_family(item, "NRNH") for item in oriented if len(item) == 4):
        candidates.append("NRNH")
    if any(_matches_family(item, "NRCH") for item in oriented if len(item) == 4):
        candidates.append("NRCH")
    if any(_matches_family(item, "NRY") for item in oriented if len(item) == 3):
        candidates.append("NRY")
    if any(_matches_family(item, "NG") for item in oriented if len(item) == 2):
        candidates.append("NGN")

    hinted = (fallback_mode or "NGG").upper()
    if hinted not in candidates:
        candidates.append(hinted)
    if "NGG" not in candidates:
        candidates.append("NGG")

    out: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def be_organism_id(species: str) -> str:
    species = (species or "").lower()
    return {
        "homo_sapiens": "1",
        "mus_musculus": "3",
        "rattus_norvegicus": "6",
        "danio_rerio": "269",
    }.get(species, "1")


async def automate_bedesigner(payload: dict) -> dict:
    sequence = clean_seq(payload.get("sequence", ""))
    pam_mode = payload.get("pam_mode", "NGG")
    species = payload.get("species", "homo_sapiens")
    title = payload.get("title", "MUTATR automated check")
    selected_guide = clean_seq(payload.get("selected_guide", ""))
    window_start = str(payload.get("bewindowstart", 13))
    window_end = str(payload.get("bewindowend", 17))

    if not sequence:
        raise ValueError("sequence is required")

    async def run_once(mode: str) -> dict:
        browser, page = await browser_page()
        try:
            await page.goto("http://www.rgenome.net/be-designer/", {"waitUntil": "networkidle2", "timeout": 30000})
            await page.type("#title", title)
            await page.click(f'#pam{be_pam_id(mode)}')
            await page.click(f'input[name="organism"][value="{be_organism_id(species)}"]')
            await page.evaluate(
                """(sequence, start, end) => {
                    document.querySelector('#query_seq').value = sequence;
                    document.querySelector('#bewindowstart').value = start;
                    document.querySelector('#bewindowend').value = end;
                }""",
                sequence,
                window_start,
                window_end,
            )
            await page.evaluate("document.forms[0].submit()")
            await page.waitForNavigation({"waitUntil": "networkidle2", "timeout": 30000})
            text = await page.evaluate("document.body.innerText")
            tables = await page.evaluate(
                """() => Array.from(document.querySelectorAll('table')).map((t, i) => {
                    const rows = Array.from(t.querySelectorAll('tr')).map((tr) =>
                      Array.from(tr.querySelectorAll('th,td')).map((cell) => (cell.innerText || '').replace(/\\s+/g, ' ').trim())
                    ).filter((cells) => cells.length);
                    const headers = rows.length ? rows[0] : [];
                    return {
                        index: i,
                        text: (t.innerText || '').slice(0, 4000),
                        headers,
                        rows: rows.slice(1)
                    };
                })"""
            )
            parsed = parse_bedesigner_match(text, tables, selected_guide)
            return {
                "url": page.url,
                "raw_text": text,
                "tables": tables,
                "parsed_match": parsed,
                "pam_mode_used": mode,
            }
        finally:
            await browser.close()

    modes = bedesigner_mode_candidates(sequence, selected_guide, pam_mode)
    best_result: dict | None = None
    for mode in modes:
        result = await run_once(mode)
        if best_result is None:
            best_result = result
        if result.get("parsed_match"):
            return result
    return best_result or {"url": "", "raw_text": "", "tables": [], "parsed_match": None, "pam_mode_used": pam_mode}


def chopchop_genome_id(species: str) -> str:
    species = (species or "").lower()
    return {
        "homo_sapiens": "hg38",
        "mus_musculus": "mm10",
        "rattus_norvegicus": "rn6",
        "danio_rerio": "danRer11",
    }.get(species, "hg38")


def chopchop_payload(payload: dict) -> dict:
    sequence = clean_seq(payload.get("sequence", ""))
    species = payload.get("species", "homo_sapiens")
    pam = clean_seq(payload.get("pam", "")) or "NGG"
    target_mode = payload.get("target_mode", "WHOLE")
    exon_target = str(payload.get("exon_target", "") or "").strip()
    if not sequence:
        raise ValueError("sequence is required")
    opts = [
        "-J",
        "-BED",
        "-GenBank",
        "-G",
        chopchop_genome_id(species),
        "-filterGCmin",
        "20",
        "-filterGCmax",
        "80",
        "-n",
        "N",
        "-R",
        "4",
        "-T",
        "1",
        "-g",
        "20",
        "-scoringMethod",
        "DOENCH_2016",
        "-f",
        "GN,NG",
        "-v",
        "3",
        "-M",
        pam,
    ]
    if target_mode == "EXON" and exon_target:
        opts.extend(["-t", "WHOLE", "-e", exon_target])
    else:
        opts.extend(["-t", "WHOLE"])
    return {
        "opts": opts,
        "fastaInput": sequence,
        "geneInput": "",
        "isIsoform": False,
        "forSelect": "knock-out",
    }


async def automate_chopchop(payload: dict) -> dict:
    submit_payload = chopchop_payload(payload)
    pam_len = max(1, len(clean_seq(payload.get("pam", "")) or "NGG"))
    selected_guides = unique_preserving([
        payload.get("selected_guide", ""),
        payload.get("selected_left_guide", ""),
        payload.get("selected_right_guide", ""),
    ])
    browser, page = await browser_page()
    try:
        await page.goto(CHOPCHOP_URL, {"waitUntil": "networkidle2", "timeout": 30000})
        response_text = await page.evaluate(
            """async (submitPayload, baseUrl) => {
                const response = await fetch(baseUrl, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(submitPayload)
                });
                return await response.text();
            }""",
            submit_payload,
            CHOPCHOP_URL,
        )
        parsed = json.loads(response_text)
        job_id = parsed.get("jobId")
        if not job_id:
            raise ValueError("CHOPCHOP did not return a job ID.")
        result_url = f"{CHOPCHOP_URL}results/{job_id}"
        body_text = ""
        parsed_rows: list[dict] = []
        for _ in range(18):
            await page.goto(result_url, {"waitUntil": "networkidle2", "timeout": 30000})
            parsed_rows = await page.evaluate(
                """() => Array.from(document.querySelectorAll('table tbody tr')).map((row) => {
                    const cells = Array.from(row.querySelectorAll('td')).map((cell) => cell.textContent.trim());
                    return {
                      rank: cells[0] || "",
                      target_sequence: cells[1] || "",
                      genomic_location: cells[2] || "",
                      strand: cells[3] || "",
                      gc_content: cells[4] || "",
                      efficiency: cells[cells.length - 1] || ""
                    };
                  })"""
            )
            body_text = await page.evaluate("document.body.innerText")
            lowered = body_text.lower()
            if parsed_rows and "loading" not in lowered and "unprocessable entity" not in lowered and len(body_text.strip()) > 500:
                break
            await asyncio.sleep(2)
        normalized_rows = []
        for row in parsed_rows:
            candidate_guides = chopchop_candidate_guides(row.get("target_sequence", ""), pam_len)
            normalized_rows.append({
                **row,
                "candidate_guides": candidate_guides,
            })
        matched_guides = []
        if selected_guides:
            for selected in selected_guides:
                if any(selected in row["candidate_guides"] for row in normalized_rows):
                    matched_guides.append(selected)
        normalized_text_parts = []
        for row in normalized_rows:
            normalized_text_parts.append(
                " | ".join([
                    f"Rank {row.get('rank', '')}",
                    f"Target sequence {row.get('target_sequence', '')}",
                    f"Guide candidates {', '.join(row.get('candidate_guides', []))}",
                    f"Location {row.get('genomic_location', '')}",
                    f"Strand {row.get('strand', '')}",
                    f"GC {row.get('gc_content', '')}",
                    f"Efficiency {row.get('efficiency', '')}",
                ])
            )
        normalized_text = "\n".join(normalized_text_parts)
        return {
            "url": result_url,
            "job_id": job_id,
            "raw_text": normalized_text or body_text,
            "raw_page_text": body_text,
            "parsed_rows": normalized_rows,
            "selected_guides": selected_guides,
            "matched_guides": matched_guides,
        }
    finally:
        await browser.close()


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        json_response(self, 200, {"ok": True})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            json_response(self, 200, {"ok": True, "service": "mutatr-automation"})
            return
        json_response(self, 404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = read_json(self)
            if path == "/automate/pegfinder":
                result = asyncio.run(automate_pegfinder(payload))
            elif path == "/automate/be-designer":
                result = asyncio.run(automate_bedesigner(payload))
            elif path == "/automate/chopchop":
                result = asyncio.run(automate_chopchop(payload))
            else:
                json_response(self, 404, {"ok": False, "error": "not found"})
                return
            json_response(self, 200, {"ok": True, "result": result})
        except Exception as error:
            json_response(self, 500, {"ok": False, "error": str(error)})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"MUTATR automation server running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
