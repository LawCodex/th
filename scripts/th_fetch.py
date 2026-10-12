#!/usr/bin/env python3
"""Fetch Thai primary legislation from the Office of the Council of State (OCS / Krisdika).

Step 1 (listing): the public law index on www.ocs.go.th
    POST https://www.ocs.go.th/searchlaw/indexs/list_table_search  (KTDatatable remote source)
  returns, per law category, the principal laws with their encrypted timeline id.
Step 2 (texts): the public JSON API of the OCS law search system (searchlaw.ocs.go.th)
    POST https://searchlaw.ocs.go.th/ocs-api/public/doc/getLawDoc
  returns the law metadata, all its timelines (versions) and the section-by-section HTML text.
  We follow the "current legislation" timeline (timelineTypeId 4) when one exists.

Raw JSON is cached under _raw/th/ so reruns do not re-download.
Usage: th_fetch.py [RAW_DIR]
"""
import datetime
import json
import os
import sys
import time
import uuid

import requests

UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
LIST_URL = "https://www.ocs.go.th/searchlaw/indexs/list_table_search"
API = "https://searchlaw.ocs.go.th/ocs-api"
DELAY = 1.0

# OCS law categories (MS_LAW_CATEGORY) that are primary legislation
CATEGORIES = [
    ("10", "constitution"),       # รัฐธรรมนูญ
    ("1A", "organic-acts"),       # พระราชบัญญัติประกอบรัฐธรรมนูญ
    ("1B,1C", "acts"),            # พระราชบัญญัติ / พระราชกำหนด
    ("1D", "codes"),              # ประมวลกฎหมาย
    ("1I,1J,1K,1L", "revolutionary"),  # ปว. / ปร. / คปค. / คสช.
    ("1F,1G,1H", "other"),        # กฎมณเฑียรบาล / พระบรมราชโองการ / กฎหมายอื่น ๆ
]

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "_raw", "th")
os.makedirs(os.path.join(RAW, "lists"), exist_ok=True)
os.makedirs(os.path.join(RAW, "docs"), exist_ok=True)

S = requests.Session()
S.headers["User-Agent"] = UA


def ensure_ca():
    """www.ocs.go.th does not send its GlobalSign intermediate certificate; build a CA bundle
    (certifi + the intermediate fetched from GlobalSign's AIA URL) so TLS stays verified."""
    import certifi
    import subprocess
    bundle = os.path.join(RAW, "ca-bundle.pem")
    if not os.path.exists(bundle):
        der = requests.get("http://secure.globalsign.com/cacert/gsrsaovsslca2018.crt",
                           headers={"User-Agent": UA}, timeout=60).content
        pem = subprocess.run(["openssl", "x509", "-inform", "DER", "-outform", "PEM"],
                             input=der, capture_output=True, check=True).stdout.decode()
        with open(bundle, "w") as f:
            f.write(open(certifi.where()).read() + "\n" + pem)
    S.verify = bundle


ensure_ca()
U1, U2 = str(uuid.uuid4()), str(uuid.uuid4())


def retry(fn, *a, **kw):
    for i in range(6):
        try:
            return fn(*a, **kw)
        except Exception as e:  # noqa
            wait = 5 * (2 ** i)
            print(f"  ! {e!r}; retry in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError("giving up")


def list_category(codes):
    out, page = [], 1
    while True:
        def go():
            r = S.post(LIST_URL, data={
                "pagination[page]": page, "pagination[perpage]": 100,
                "query[tab_type]": "law", "query[type_view]": "law", "query[q]": "",
                "query[topic]": 1, "query[content]": 0, "query[sublaw]": 0, "query[synonyms]": 0,
                "query[lawCategoryName]": codes, "query[stateName]": "01,02",
                "query[onlyMatchChild]": 0, "query[sort]": "default", "query[letter]": "",
            }, timeout=120)
            r.raise_for_status()
            return r.json()
        d = retry(go)
        time.sleep(DELAY)
        out.extend(d.get("data") or [])
        if page >= int(d["meta"].get("pages") or 1):
            return out
        page += 1


def api(path, service, body):
    hdr = {"reqId": str(int(time.time() * 1000)), "reqChannel": "WEB",
           "reqDtm": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000"),
           "reqBy": "unknow", "serviceName": service, "uuid": U1, "sessionId": U2}

    def go():
        r = S.post(API + path, json={"reqHeader": hdr, "reqBody": body}, timeout=180)
        r.raise_for_status()
        j = r.json()
        if j.get("respHeader", {}).get("errorCode") != "SUCCESS":
            raise RuntimeError(f"{service}: {j.get('respHeader')}")
        return j["respBody"]
    res = retry(go)
    time.sleep(DELAY)
    return res


def get_doc(tid):
    return api("/public/doc/getLawDoc", "getPublicLawDoc", {"isTransEng": False, "timelineId": tid})


def main():
    for codes, name in CATEGORIES:
        lf = os.path.join(RAW, "lists", name + ".json")
        if os.path.exists(lf):
            items = json.load(open(lf, encoding="utf-8"))
        else:
            items = list_category(codes)
            json.dump(items, open(lf, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"{name}: {len(items)} items", flush=True)
        for n, it in enumerate(items):
            code = it["lawCode"]
            df = os.path.join(RAW, "docs", code + ".json")
            if os.path.exists(df):
                continue
            try:
                doc = get_doc(it["encTimelineID"])
                cur = [t for t in doc.get("timelines") or [] if t.get("timelineTypeId") == "4"]
                if cur and cur[-1]["timelineId"] != doc["lawInfo"]["timelineId"]:
                    doc = get_doc(cur[-1]["timelineId"])
            except Exception as e:  # noqa
                print(f"  FAIL {code}: {e}", flush=True)
                continue
            doc["_list"] = {k: it.get(k) for k in ("lawCode", "lawNameTh", "encTimelineID", "year", "publishDate")}
            doc["_category"] = name
            json.dump(doc, open(df, "w", encoding="utf-8"), ensure_ascii=False)
            if n % 50 == 0:
                print(f"  {name} {n}/{len(items)} {code}", flush=True)


if __name__ == "__main__":
    main()
