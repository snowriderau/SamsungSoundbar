#!/usr/bin/env python3
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOC = Path("/private/tmp/wam_api_doc/API_Methods.md")
CONFIG = DATA / "config.json"

CATALOG_JSON = DATA / "wam_method_catalog.json"
PROBE_JSON = DATA / "deep_probe_results.json"
PROBE_MD = DATA / "deep_probe_summary.md"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def parse_doc_sections(text: str):
    parts = re.split(r"\n(?=###\s+\d+\s+-\s+[A-Za-z0-9_]+)", text)
    sections = []
    for part in parts:
        m = re.match(r"###\s+(\d+)\s+-\s+([A-Za-z0-9_]+)", part)
        if not m:
            continue
        idx = int(m.group(1))
        method = m.group(2)

        desc_m = re.search(r"Description:\s*(.*)", part)
        desc = desc_m.group(1).strip() if desc_m else "---"

        endpoint = "UIC"
        curl_m = re.search(r"http://[^\n']+/(UIC|CPM)\?cmd=", part)
        if curl_m:
            endpoint = curl_m.group(1)

        xml_blocks = re.findall(r"Xml string decoded:\s*```\s*(.*?)\s*```", part, flags=re.S)
        payloads = []
        for blk in xml_blocks:
            xml = "".join(line.strip() for line in blk.splitlines() if line.strip())
            if "<name>" not in xml:
                xml = f"<name>{method}</name>"
            payloads.append(xml)
        if not payloads:
            payloads = [f"<name>{method}</name>"]

        params = []
        for payload in payloads:
            for pm in re.finditer(r"<p\s+type=\"([^\"]+)\"\s+name=\"([^\"]+)\"\s+val=\"([^\"]*)\"", payload):
                params.append({"type": pm.group(1), "name": pm.group(2), "val": pm.group(3)})

        sections.append({
            "index": idx,
            "method": method,
            "endpoint": endpoint,
            "description": desc,
            "sample_payloads": payloads,
            "params": params,
        })
    return sections


def send(ip: str, port: int, endpoint: str, xml: str, timeout: float = 1.25):
    q = urllib.parse.quote(xml, safe="")
    url = f"http://{ip}:{port}/{endpoint}?cmd={q}"
    req = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(6000).decode("utf-8", errors="replace")
            return {"http_status": int(r.status), "body": body, "error": None, "url": url}
    except urllib.error.HTTPError as e:
        body = e.read(3000).decode("utf-8", errors="replace")
        return {"http_status": int(e.code), "body": body, "error": f"HTTP {e.code}", "url": url}
    except Exception as e:
        return {"http_status": None, "body": "", "error": str(e), "url": url}


def parse_response(body: str):
    if not body:
        return {"xml_ok": False, "result": None, "method": None, "err": None}
    try:
        root = ET.fromstring(body)
        response = root.find(".//response")
        result = response.attrib.get("result") if response is not None else None
        method = root.findtext("method")
        err = root.findtext(".//errCode")
        return {"xml_ok": True, "result": result, "method": method, "err": err}
    except Exception:
        return {"xml_ok": False, "result": None, "method": None, "err": None}


def classify(http_status, parsed, error):
    if parsed.get("result") == "ok":
        return "working"
    if parsed.get("result") == "ng":
        return "recognized_but_rejected"
    if error:
        return "transport_error"
    if http_status == 200 and parsed.get("xml_ok"):
        return "responded_unknown"
    return "unknown"


def param_xml(name, ptype, val):
    if ptype == "cdata":
        return f'<p type="cdata" name="{name}" val="empty"><![CDATA[{val}]]></p>'
    return f'<p type="{ptype}" name="{name}" val="{val}"/>'


def build_candidates(catalog):
    # Avoid commands likely to break network config.
    banned = {"SetIpInfo"}

    methods = {}
    for row in catalog:
        m = row["method"]
        if m in banned:
            continue
        methods.setdefault(m, {"method": m, "endpoints": set(), "descriptions": set(), "payloads": [], "params": []})
        methods[m]["endpoints"].add(row["endpoint"])
        methods[m]["descriptions"].add(row["description"])
        methods[m]["payloads"].extend(row["sample_payloads"])
        methods[m]["params"].extend(row["params"])

    candidates = []

    # 1) Baseline method probes and documented payloads.
    for m, info in sorted(methods.items()):
        endpoint = "UIC" if "UIC" in info["endpoints"] else list(info["endpoints"])[0]
        candidates.append({"method": m, "endpoint": endpoint, "xml": f"<name>{m}</name>", "source": "base"})
        for p in info["payloads"][:4]:
            candidates.append({"method": m, "endpoint": endpoint, "xml": p, "source": "doc-sample"})

    # 2) Focused power + volume permutations.
    focus = [
        ("PowerOn", "UIC", ["<name>PowerOn</name>"]),
        ("PowerOff", "UIC", ["<name>PowerOff</name>"]),
        ("GetPowerStatus", "UIC", ["<name>GetPowerStatus</name>"]),
        ("SetPowerStatus", "UIC", [
            '<name>SetPowerStatus</name><p type="str" name="power" val="on"/>',
            '<name>SetPowerStatus</name><p type="str" name="power" val="off"/>',
            '<name>SetPowerStatus</name><p type="str" name="status" val="on"/>',
            '<name>SetPowerStatus</name><p type="str" name="status" val="off"/>',
            '<name>SetPowerStatus</name><p type="dec" name="power" val="1"/>',
            '<name>SetPowerStatus</name><p type="dec" name="power" val="0"/>',
        ]),
        ("VolumeUp", "UIC", ["<name>VolumeUp</name>"]),
        ("VolumeDown", "UIC", ["<name>VolumeDown</name>"]),
        ("SetVolume", "UIC", [
            '<name>SetVolume</name><p type="dec" name="volume" val="1"/>',
            '<name>SetVolume</name><p type="dec" name="volume" val="5"/>',
            '<name>SetVolume</name><p type="dec" name="volume" val="10"/>',
            '<name>SetVolume</name><p type="dec" name="volume" val="20"/>',
            '<name>SetVolume</name><p type="str" name="volume" val="up"/>',
            '<name>SetVolume</name><p type="str" name="volume" val="down"/>',
            '<name>SetVolume</name><p type="str" name="mode" val="up"/>',
            '<name>SetVolume</name><p type="str" name="mode" val="down"/>',
            '<name>SetVolume</name><p type="dec" name="step" val="1"/>',
            '<name>SetVolume</name><p type="dec" name="delta" val="1"/>',
            '<name>SetVolume</name><p type="dec" name="delta" val="-1"/>',
        ]),
    ]
    for method, endpoint, payloads in focus:
        for xml in payloads:
            candidates.append({"method": method, "endpoint": endpoint, "xml": xml, "source": "focus"})

    # 3) Generic param-pattern sweep for Set* methods.
    common_names = [
        "mode", "state", "status", "value", "index", "presetindex", "volume", "wooferlevel",
        "mute", "function", "shufflemode", "repeatmode", "playbackcontrol", "trickmode"
    ]
    dec_values = ["0", "1", "-1", "2", "5", "6", "10", "20", "50", "100"]
    str_values = ["on", "off", "up", "down", "play", "pause", "next", "prev", "standard", "surround", "game", "smart", "bt", "wifi", "arc", "hdmi1", "hdmi2"]

    for m, info in sorted(methods.items()):
        if not m.startswith("Set"):
            continue
        endpoint = "UIC" if "UIC" in info["endpoints"] else list(info["endpoints"])[0]
        pnames = [p["name"] for p in info["params"]]
        names = list(dict.fromkeys(pnames + common_names))[:8]

        for name in names:
            for val in dec_values[:6]:
                xml = f"<name>{m}</name>{param_xml(name, 'dec', val)}"
                candidates.append({"method": m, "endpoint": endpoint, "xml": xml, "source": "pattern-dec"})
            for val in str_values[:8]:
                xml = f"<name>{m}</name>{param_xml(name, 'str', val)}"
                candidates.append({"method": m, "endpoint": endpoint, "xml": xml, "source": "pattern-str"})
            for sval in ["test", "public", "none"]:
                xml = f"<name>{m}</name>{param_xml(name, 'cdata', sval)}"
                candidates.append({"method": m, "endpoint": endpoint, "xml": xml, "source": "pattern-cdata"})

    # Dedupe and cap while still "thousands".
    out, seen = [], set()
    for c in candidates:
        key = (c["endpoint"], c["xml"])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)

    if len(out) < 1200:
        # ensure wider deep sweep by adding alternate endpoints for unknowns
        extra = []
        for c in out[:400]:
            alt = "CPM" if c["endpoint"] == "UIC" else "UIC"
            extra.append({**c, "endpoint": alt, "source": c["source"] + "-alt-endpoint"})
        for c in extra:
            key = (c["endpoint"], c["xml"])
            if key not in seen:
                seen.add(key)
                out.append(c)

    return out[:2600], methods


def run_probe(ip: str, port: int, candidates: list[dict]):
    results = []

    def worker(i, cand):
        resp = send(ip, port, cand["endpoint"], cand["xml"])
        parsed = parse_response(resp["body"])
        cls = classify(resp["http_status"], parsed, resp["error"])
        return {
            "index": i,
            "tested_at": now_iso(),
            "method": cand["method"],
            "endpoint": cand["endpoint"],
            "xml": cand["xml"],
            "source": cand["source"],
            "classification": cls,
            "http_status": resp["http_status"],
            "error": resp["error"],
            "response_method": parsed["method"],
            "result": parsed["result"],
            "err_code": parsed["err"],
            "body": resp["body"][:1400],
        }

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = [ex.submit(worker, i + 1, c) for i, c in enumerate(candidates)]
        for n, fut in enumerate(as_completed(futures), start=1):
            row = fut.result()
            results.append(row)
            if n % 100 == 0:
                print(f"completed {n}/{len(candidates)}")

    results.sort(key=lambda r: r["index"])
    return results


def write_summary(catalog, methods_map, results, ip, port):
    by_class = {}
    for r in results:
        by_class.setdefault(r["classification"], []).append(r)

    power_vol = [r for r in results if r["method"].lower() in {
        "poweron", "poweroff", "getpowerstatus", "setpowerstatus", "setvolume", "volumeup", "volumedown", "getvolume"
    }]

    # Build description map.
    descriptions = {}
    for row in catalog:
        descriptions.setdefault(row["method"], set()).add(row.get("description", "---"))

    lines = []
    lines.append(f"# Deep Probe Summary ({now_iso()})")
    lines.append("")
    lines.append(f"Target: `{ip}:{port}`")
    lines.append(f"Total probes: **{len(results)}**")
    lines.append(f"Working: **{len(by_class.get('working', []))}**")
    lines.append(f"Recognized but rejected: **{len(by_class.get('recognized_but_rejected', []))}**")
    lines.append(f"Transport errors: **{len(by_class.get('transport_error', []))}**")
    lines.append("")
    lines.append("## Power / Volume Focus")
    for r in power_vol:
        lines.append(f"- `{r['method']}` [{r['classification']}] `{r['xml']}`")

    lines.append("")
    lines.append("## Working Methods (unique)")
    work_methods = sorted({r["method"] for r in by_class.get("working", [])})
    for m in work_methods:
        desc = "; ".join(sorted(descriptions.get(m, {"---"})))
        lines.append(f"- `{m}`: {desc}")

    lines.append("")
    lines.append("## Methods With No Description In Doc")
    for m, meta in sorted(methods_map.items()):
        descs = [d for d in meta["descriptions"] if d and d != "---"]
        if not descs:
            lines.append(f"- `{m}`")

    lines.append("")
    lines.append("## Pattern Notes")
    lines.append("- `Get*` methods usually work with `<name>Method</name>` only.")
    lines.append("- `Set*` methods often return `Invalid parameter number` when parameter count/name/type mismatch.")
    lines.append("- For this soundbar, working setter patterns observed include `type=\"dec\"` for numeric fields (`volume`, `wooferlevel`, `presetindex`, `eqvalue1..7`).")
    lines.append("- `type=\"str\"` is required for enum-like fields (`mute`, `function`, some mode/select operations).")
    lines.append("- `type=\"cdata\"` appears mainly for titles/names/metadata and is usually irrelevant for core remote controls.")

    PROBE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if not DOC.exists():
        raise SystemExit(f"Missing API doc: {DOC}")

    cfg = load_json(CONFIG, {"ip": "", "port": 56001})
    ip, port = cfg.get("ip", ""), int(cfg.get("port", 56001))
    if not ip:
        raise SystemExit("No IP in data/config.json")

    text = DOC.read_text(encoding="utf-8", errors="ignore")
    catalog = parse_doc_sections(text)
    CATALOG_JSON.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    candidates, methods_map = build_candidates(catalog)
    print(f"Catalog methods: {len(methods_map)} | candidates: {len(candidates)}")

    results = run_probe(ip, port, candidates)
    out = {
        "run_at": now_iso(),
        "target": f"{ip}:{port}",
        "total": len(results),
        "results": results,
    }
    PROBE_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    write_summary(catalog, methods_map, results, ip, port)

    print(f"Wrote {CATALOG_JSON}")
    print(f"Wrote {PROBE_JSON}")
    print(f"Wrote {PROBE_MD}")


if __name__ == "__main__":
    main()
