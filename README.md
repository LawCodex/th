# Thailand — LawCodex

Thai legislation as plain Markdown, in Thai (the only official language), taken from the
official consolidated texts of the **Office of the Council of State (OCS, สำนักงานคณะกรรมการกฤษฎีกา /
Krisdika)**. Part of [LawCodex](https://github.com/LawCodex).

## What is covered

Primary legislation as published in the OCS law database, in its **current consolidated
version** ("ฉบับปรับปรุงล่าสุด", timeline type 4) where the OCS provides one, otherwise the
principal version:

| Category | Thai | Directory | Files |
|---|---|---|---|
| Constitution in force (B.E. 2560 / 2017, as amended) | รัฐธรรมนูญ | `constitution/` | 1 |
| Earlier (repealed) constitutions, for reference | รัฐธรรมนูญ (ยกเลิก) | `constitution/historical/` | 15 |
| Organic Acts | พระราชบัญญัติประกอบรัฐธรรมนูญ | `organic-acts/` | 10 |
| Codes | ประมวลกฎหมาย | `codes/` | 8 |
| Acts and Emergency Decrees | พระราชบัญญัติ / พระราชกำหนด | `acts/<B.E. year>/` | 1,025 |
| Announcements/orders of revolutionary councils having the force of law (ปว., ปร., คปค., คสช.) | ประกาศ/คำสั่งคณะปฏิวัติ ฯลฯ | `revolutionary/<B.E. year>/` | 226 |
| **Total** | | | **1,285** |

Only laws listed by the OCS index as in force (state "ยังมีผลใช้บังคับ" or "ประกาศรอมีผลใช้บังคับ")
are included; 601 index entries whose title is marked "(ยกเลิก)" (repealed) are skipped, except for the
historical constitutions. Laws announced but not yet in force have `status: not_yet_in_force`.

### Not covered

- Subordinate legislation (พระราชกฤษฎีกา royal decrees, กฎกระทรวง ministerial regulations,
  ประกาศ notifications, ระเบียบ rules, local ordinances, …) — tens of thousands of instruments;
  the OCS database holds them under the same API and `scripts/th_fetch.py` can be extended with
  the corresponding category codes (2A, 2B, …).
- English translations published by the OCS (unofficial).
- The Royal Gazette (ราชกิจจานุเบกษา) original publications (PDF scans).
- Images embedded in a few laws (forms, emblems) are dropped; tables are kept as HTML.

## Format

One Markdown file per law, with YAML front matter (`title`, `title_en` when the OCS gives an
English title, `identifier` = OCS law code, `type`, `date` = promulgation/publication date,
`last_amended` = date of the consolidated version, `status`, `source`, `retrieved`).
Structural divisions (บรรพ/ภาค, ลักษณะ, หมวด, ส่วน, บทเฉพาะกาล) become headings; each มาตรา / ข้อ is
a heading. Transitional provisions of amending acts, which the OCS appends after the consolidated
text, follow under a `##` heading with the amending act's title. OCS footnotes (Royal Gazette
references, amendment history) are kept as Markdown footnotes.

File names are the OCS law code transliterated to ASCII (Thai consonant → RTGS initial, e.g.
`ร0006-10-0001` → `r0006-10-0001`); directories for Acts use the Buddhist-era (B.E.) year of
promulgation. The native title is in the front matter and the H1.

## Sources

- Law index (listing, with encrypted timeline IDs): `POST https://www.ocs.go.th/searchlaw/indexs/list_table_search`
  (the backend of https://www.ocs.go.th/searchlaw-law).
- Law texts: OCS law search system JSON API,
  `POST https://searchlaw.ocs.go.th/ocs-api/public/doc/getLawDoc` (backend of
  https://searchlaw.ocs.go.th/council-of-state/). Each file's `source` links to the public page
  of the consolidated version.

Retrieved: 2026-10-12. No robots.txt is published on either host; requests were sequential with
a 1 s delay and a descriptive User-Agent. `www.ocs.go.th` does not serve its intermediate TLS
certificate; the fetch script adds the GlobalSign intermediate (from GlobalSign's AIA URL) to the
CA bundle rather than disabling verification. (The legacy host `www.krisdika.go.th` presents a
self-signed certificate and now only returns 404, so it was not used.)

## Copyright

Under section 7 of the Thai Copyright Act B.E. 2537 (1994), the Constitution and laws, royal
decrees, regulations and similar official texts are **not copyright works**. The texts here are
reproduced for public information; the OCS consolidations are not themselves authoritative —
the Royal Gazette is.

## Regenerate

```sh
pip install -r scripts/requirements.txt
python scripts/th_fetch.py  ../_raw/th      # listing + JSON per law (cached)
python scripts/th_convert.py ../_raw/th .   # Markdown
```
