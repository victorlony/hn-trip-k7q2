"""Write flight.json with live Taoyuan airport status for the flights listed in the trip sheet."""
import csv, io, json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

SHEET_ID = "1iplKftKuIunkN6rGhfapRGIX3zFFtqDZRD-YfH6eHeU"
FIDS = "https://www.taoyuan-airport.com/uploads/flightx/a_flight_v4.txt"
TW = timezone(timedelta(hours=8))
YEAR = 2026


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def flights_from_sheet():
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&headers=1&sheet="
           + urllib.parse.quote("基本資料"))
    rows = csv.DictReader(io.StringIO(get(url).decode("utf-8")))
    text = next((r["內容"] for r in rows if r.get("欄位") == "班機與時差"), "")
    out = []
    for m in re.finditer(r"([A-Z0-9]{2})\s?(\d{1,4})\s+(\d{1,2})/(\d{1,2})", text):
        out.append((m[1], int(m[2]), f"{YEAR}/{int(m[3]):02d}/{int(m[4]):02d}"))
    return out


def main(path):
    now = datetime.now(TW)
    wanted = flights_from_sheet()
    soon = [f for f in wanted if abs((datetime.strptime(f[2], "%Y/%m/%d").replace(tzinfo=TW) - now).days) <= 1]
    data = {"updated": now.isoformat(timespec="seconds"), "flights": []}
    if soon:
        for line in get(FIDS).decode("big5", "replace").splitlines():
            c = [x.strip() for x in line.split(",")]
            if len(c) < 14 or not c[4].isdigit():
                continue
            for air, num, date in soon:
                if c[2] == air and int(c[4]) == num and c[6] == date:
                    data["flights"].append({
                        "no": f"{air}{num}", "date": date, "dir": "dep" if c[1] == "D" else "arr",
                        "gate": c[5], "sched": c[7][:5], "estDate": c[8], "est": c[9][:5],
                        "status": re.sub(r"[A-Z ]+$", "", c[13]).strip() or c[13], "terminal": c[0],
                        "belt": c[18] if len(c) > 18 else "", "counter": c[19] if len(c) > 19 else "",
                    })
    old = None
    try:
        old = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if old and old.get("flights") == data["flights"]:
        print("unchanged")
        return
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "flight.json")
