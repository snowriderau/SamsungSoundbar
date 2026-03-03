#!/usr/bin/env python3
import json
import re
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG_PATH = DATA / "config.json"
NAMES_PATH = DATA / "discovered_command_names.txt"
RESULTS_PATH = DATA / "bruteforce_results.json"
SUMMARY_PATH = DATA / "bruteforce_summary.md"
COMMANDS_PATH = DATA / "commands.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def send_cmd(ip: str, port: int, xml_command: str, timeout: float = 2.8) -> dict:
    encoded = urllib.parse.quote(xml_command, safe="")
    url = f"http://{ip}:{port}/UIC?cmd={encoded}"
    req = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(8000).decode("utf-8", errors="replace")
            return {"ok": True, "http_status": int(resp.status), "body": body, "url": url, "error": None}
    except urllib.error.HTTPError as exc:
        body = exc.read(4000).decode("utf-8", errors="replace")
        return {"ok": False, "http_status": int(exc.code), "body": body, "url": url, "error": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"ok": False, "http_status": None, "body": "", "url": url, "error": str(exc)}


def parse_response(body: str) -> dict:
    if not body:
        return {"xml_ok": False, "method": None, "result": None, "err_code": None}
    try:
        root = ET.fromstring(body)
        method = root.findtext("method")
        response = root.find(".//response")
        result = response.attrib.get("result") if response is not None else None
        err = root.findtext(".//errCode")
        return {"xml_ok": True, "method": method, "result": result, "err_code": err}
    except Exception:
        return {"xml_ok": False, "method": None, "result": None, "err_code": None}


def classify(http_ok: bool, parsed: dict, error: str | None) -> str:
    if error and not http_ok:
        return "transport_error"
    if parsed.get("result") == "ok":
        return "working"
    if parsed.get("result") == "ng":
        return "recognized_but_rejected"
    if http_ok and parsed.get("xml_ok"):
        return "responded_unknown"
    return "unknown"


def build_candidates(names: list[str]) -> list[dict]:
    items = []

    filtered = [n for n in names if re.fullmatch(r"(?:Get|Set)[A-Za-z0-9]+", n)]
    for cmd in sorted(set(filtered)):
        items.append({"name": cmd, "xml": f"<name>{cmd}</name>", "source": "name-scan"})

    # Focused sweeps for soundbar controls the user asked for.
    items.extend([
        {"name": "GetWooferLevel", "xml": "<name>GetWooferLevel</name>", "source": "focus"},
        {"name": "SetWooferLevel", "xml": "<name>SetWooferLevel</name><p type=\"dec\" name=\"wooferlevel\" val=\"6\"/>", "source": "focus"},
        {"name": "SetWooferLevel", "xml": "<name>SetWooferLevel</name><p type=\"dec\" name=\"wooferlevel\" val=\"-6\"/>", "source": "focus"},
        {"name": "SetWooferLevel", "xml": "<name>SetWooferLevel</name><p type=\"int\" name=\"woofer\" val=\"6\"/>", "source": "focus"},
        {"name": "SetWooferLevel", "xml": "<name>SetWooferLevel</name><p type=\"int\" name=\"woofer\" val=\"-6\"/>", "source": "focus"},
        {"name": "SetSubWooferLevel", "xml": "<name>SetSubWooferLevel</name><p type=\"dec\" name=\"wooferlevel\" val=\"6\"/>", "source": "focus"},
        {"name": "GetEQBalance", "xml": "<name>GetEQBalance</name>", "source": "focus"},
        {"name": "SetEQBalance", "xml": "<name>SetEQBalance</name><p type=\"int\" name=\"balance\" val=\"0\"/>", "source": "focus"},
        {"name": "GetSoundMode", "xml": "<name>GetSoundMode</name>", "source": "focus"},
        {"name": "SetSoundMode", "xml": "<name>SetSoundMode</name><p type=\"str\" name=\"mode\" val=\"standard\"/>", "source": "focus"},
        {"name": "SetSoundMode", "xml": "<name>SetSoundMode</name><p type=\"str\" name=\"mode\" val=\"surround\"/>", "source": "focus"},
        {"name": "SetSoundMode", "xml": "<name>SetSoundMode</name><p type=\"str\" name=\"mode\" val=\"game\"/>", "source": "focus"},
        {"name": "SetSoundMode", "xml": "<name>SetSoundMode</name><p type=\"str\" name=\"mode\" val=\"smart\"/>", "source": "focus"},
        {"name": "GetBass", "xml": "<name>GetBass</name>", "source": "focus"},
        {"name": "SetBass", "xml": "<name>SetBass</name><p type=\"dec\" name=\"bass\" val=\"6\"/>", "source": "focus"},
        {"name": "SetBass", "xml": "<name>SetBass</name><p type=\"dec\" name=\"bass\" val=\"-6\"/>", "source": "focus"},
        {"name": "GetTreble", "xml": "<name>GetTreble</name>", "source": "focus"},
        {"name": "SetTreble", "xml": "<name>SetTreble</name><p type=\"dec\" name=\"treble\" val=\"6\"/>", "source": "focus"},
        {"name": "SetTreble", "xml": "<name>SetTreble</name><p type=\"dec\" name=\"treble\" val=\"-6\"/>", "source": "focus"},
        {"name": "Get7BandEQList", "xml": "<name>Get7BandEQList</name>", "source": "focus"},
        {"name": "GetCurrentEQMode", "xml": "<name>GetCurrentEQMode</name>", "source": "focus"},
        {"name": "Set7bandEQMode", "xml": "<name>Set7bandEQMode</name><p type=\"dec\" name=\"presetindex\" val=\"1\"/>", "source": "focus"},
        {"name": "Set7bandEQValue", "xml": "<name>Set7bandEQValue</name><p type=\"dec\" name=\"presetindex\" val=\"4\"/><p type=\"dec\" name=\"eqvalue1\" val=\"0\"/><p type=\"dec\" name=\"eqvalue2\" val=\"0\"/><p type=\"dec\" name=\"eqvalue3\" val=\"0\"/><p type=\"dec\" name=\"eqvalue4\" val=\"0\"/><p type=\"dec\" name=\"eqvalue5\" val=\"0\"/><p type=\"dec\" name=\"eqvalue6\" val=\"0\"/><p type=\"dec\" name=\"eqvalue7\" val=\"0\"/>", "source": "focus"},
    ])

    # dedupe by xml payload
    out = []
    seen = set()
    for item in items:
        if item["xml"] in seen:
            continue
        seen.add(item["xml"])
        out.append(item)
    return out


def merge_into_commands(results: list[dict]) -> None:
    commands = load_json(COMMANDS_PATH, [])
    by_xml = {c.get("xml_command"): c for c in commands}
    now = utc_now()

    for res in results:
        if res["classification"] not in {"working", "recognized_but_rejected"}:
            continue
        xml = res["xml"]
        status = "working" if res["classification"] == "working" else "not_working"
        if xml in by_xml:
            existing = by_xml[xml]
            existing["last_tested_at"] = now
            existing["last_http_status"] = res.get("http_status")
            existing["last_error"] = res.get("error")
            existing["last_response"] = res.get("body", "")[:2000]
            if status == "working":
                existing["status"] = "working"
            continue

        cmd_id = re.sub(r"[^a-z0-9]+", "-", res["name"].lower()).strip("-") or "cmd"
        suffix = 1
        ids = {c.get("id") for c in commands}
        candidate = cmd_id
        while candidate in ids:
            suffix += 1
            candidate = f"{cmd_id}-{suffix}"

        commands.append({
            "id": candidate,
            "name": res["name"],
            "xml_command": xml,
            "expected": f"Discovered by brute-force ({res['classification']})",
            "status": status,
            "last_tested_at": now,
            "last_http_status": res.get("http_status"),
            "last_error": res.get("error"),
            "last_response": res.get("body", "")[:2000],
        })

    COMMANDS_PATH.write_text(json.dumps(commands, indent=2), encoding="utf-8")


def main():
    cfg = load_json(CONFIG_PATH, {"ip": "", "port": 56001})
    ip = cfg.get("ip", "")
    port = int(cfg.get("port", 56001))
    if not ip:
        raise SystemExit("No IP configured in data/config.json")

    names = []
    if NAMES_PATH.exists():
        names = [line.strip() for line in NAMES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]

    candidates = build_candidates(names)
    results = []

    for idx, item in enumerate(candidates, start=1):
        response = send_cmd(ip, port, item["xml"])
        parsed = parse_response(response["body"])
        classification = classify(bool(response.get("http_status") == 200), parsed, response.get("error"))
        record = {
            "index": idx,
            "tested_at": utc_now(),
            "name": item["name"],
            "xml": item["xml"],
            "source": item["source"],
            "classification": classification,
            "http_status": response.get("http_status"),
            "error": response.get("error"),
            "method": parsed.get("method"),
            "result": parsed.get("result"),
            "err_code": parsed.get("err_code"),
            "body": response.get("body", "")[:2000],
        }
        results.append(record)
        print(f"[{idx:03d}/{len(candidates)}] {item['name']}: {classification} ({record['http_status']}, {record['err_code'] or record['error'] or 'ok'})")

    summary = {
        "run_at": utc_now(),
        "target": f"{ip}:{port}",
        "total_tested": len(results),
        "working": [r for r in results if r["classification"] == "working"],
        "recognized_but_rejected": [r for r in results if r["classification"] == "recognized_but_rejected"],
        "transport_error": [r for r in results if r["classification"] == "transport_error"],
        "unknown": [r for r in results if r["classification"] not in {"working", "recognized_but_rejected", "transport_error"}],
        "all": results,
    }

    RESULTS_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = []
    lines.append(f"# Brute Force Summary ({summary['run_at']})")
    lines.append("")
    lines.append(f"Target: `{summary['target']}`")
    lines.append(f"Total tested: **{summary['total_tested']}**")
    lines.append(f"Working: **{len(summary['working'])}**")
    lines.append(f"Recognized but rejected: **{len(summary['recognized_but_rejected'])}**")
    lines.append(f"Transport error/timeouts: **{len(summary['transport_error'])}**")
    lines.append("")
    lines.append("## Working Commands")
    for r in summary["working"]:
        lines.append(f"- `{r['name']}` -> `{r['xml']}`")
    lines.append("")
    lines.append("## Recognized But Rejected")
    for r in summary["recognized_but_rejected"]:
        err = r.get("err_code") or "ng"
        lines.append(f"- `{r['name']}` ({err}) -> `{r['xml']}`")

    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    merge_into_commands(results)
    print(f"\nWrote {RESULTS_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    print(f"Updated {COMMANDS_PATH}")


if __name__ == "__main__":
    main()
