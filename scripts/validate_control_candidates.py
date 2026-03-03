#!/usr/bin/env python3
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = DATA / "config.json"
OUT = DATA / "control_validation.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_cfg():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    return cfg["ip"], int(cfg.get("port", 56001))


def send(ip, port, xml, timeout=2.5):
    url = f"http://{ip}:{port}/UIC?cmd=" + urllib.parse.quote(xml, safe="")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read(5000).decode("utf-8", errors="replace")
            x = ET.fromstring(body)
            response = x.find(".//response")
            result = response.attrib.get("result") if response is not None else None
            err = x.findtext(".//errCode")
            return {
                "ok": result == "ok",
                "result": result,
                "err": err,
                "method": x.findtext("method"),
                "body": body,
            }
    except Exception as e:
        return {"ok": False, "result": None, "err": str(e), "method": None, "body": ""}


def get_volume(ip, port):
    r = send(ip, port, "<name>GetVolume</name>")
    if not r["ok"]:
        return None
    try:
        x = ET.fromstring(r["body"])
        t = x.findtext(".//volume")
        return int(t) if t is not None else None
    except Exception:
        return None


def get_power(ip, port):
    r = send(ip, port, "<name>GetPowerStatus</name>")
    if not r["ok"]:
        return None
    try:
        x = ET.fromstring(r["body"])
        v = x.findtext(".//powerStatus")
        return int(v) if v is not None else None
    except Exception:
        return None


def test_action(ip, port, label, xml, kind, repeats=4):
    rows = []
    for _ in range(repeats):
        if kind == "volume":
            before = get_volume(ip, port)
        elif kind == "power":
            before = get_power(ip, port)
        else:
            before = None

        resp = send(ip, port, xml)
        time.sleep(0.8)

        if kind == "volume":
            after = get_volume(ip, port)
        elif kind == "power":
            after = get_power(ip, port)
        else:
            after = None

        changed = (before is not None and after is not None and before != after)
        rows.append({
            "before": before,
            "after": after,
            "changed": changed,
            "result": resp.get("result"),
            "err": resp.get("err"),
        })

    ok_count = sum(1 for r in rows if r["result"] == "ok")
    changed_count = sum(1 for r in rows if r["changed"])
    return {
        "label": label,
        "xml": xml,
        "kind": kind,
        "ok_ratio": f"{ok_count}/{repeats}",
        "change_ratio": f"{changed_count}/{repeats}",
        "rows": rows,
    }


def main():
    ip, port = load_cfg()
    tests = [
        ("power_on", "<name>PowerOn</name>", "power"),
        ("power_off", "<name>PowerOff</name>", "power"),
        ("set_power_1", "<name>SetPowerStatus</name><p type=\"dec\" name=\"power\" val=\"1\"/>", "power"),
        ("set_power_0", "<name>SetPowerStatus</name><p type=\"dec\" name=\"power\" val=\"0\"/>", "power"),
        ("volume_up", "<name>VolumeUp</name>", "volume"),
        ("volume_down", "<name>VolumeDown</name>", "volume"),
        ("set_volume_up_str", "<name>SetVolume</name><p type=\"str\" name=\"volume\" val=\"up\"/>", "volume"),
        ("set_volume_down_str", "<name>SetVolume</name><p type=\"str\" name=\"volume\" val=\"down\"/>", "volume"),
        ("set_volume_delta_plus", "<name>SetVolume</name><p type=\"dec\" name=\"delta\" val=\"1\"/>", "volume"),
        ("set_volume_delta_minus", "<name>SetVolume</name><p type=\"dec\" name=\"delta\" val=\"-1\"/>", "volume"),
        ("set_volume_abs_4", "<name>SetVolume</name><p type=\"dec\" name=\"volume\" val=\"4\"/>", "volume"),
        ("set_volume_abs_10", "<name>SetVolume</name><p type=\"dec\" name=\"volume\" val=\"10\"/>", "volume"),
    ]

    results = [test_action(ip, port, label, xml, kind) for label, xml, kind in tests]
    payload = {"run_at": now_iso(), "target": f"{ip}:{port}", "results": results}
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    for r in results:
        print(f"{r['label']}: ok {r['ok_ratio']} | state-change {r['change_ratio']}")


if __name__ == "__main__":
    main()
