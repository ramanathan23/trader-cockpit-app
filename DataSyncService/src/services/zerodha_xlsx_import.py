from __future__ import annotations

import base64
import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

import asyncpg

from .zerodha_pnl_import import import_pnl_rows

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def colnum(ref: str) -> int:
    n = 0
    for ch in "".join(c for c in ref if c.isalpha()):
        n = n * 26 + ord(ch) - 64
    return n


def strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.findall(".//a:t", NS)) for si in root.findall("a:si", NS)]


def sheet_paths(z: zipfile.ZipFile):
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rel = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rels = {x.attrib["Id"]: x.attrib["Target"] for x in rel}
    for sheet in wb.findall(".//a:sheet", NS):
        rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        yield sheet.attrib["name"], "xl/" + rels[rid].lstrip("/")


def read_sheet(z: zipfile.ZipFile, path: str, shared: list[str]) -> list[list[str]]:
    root, rows = ET.fromstring(z.read(path)), []
    for row in root.findall(".//a:sheetData/a:row", NS):
        cells = {}
        for cell in row.findall("a:c", NS):
            val = cell.find("a:v", NS)
            text = "" if val is None else val.text or ""
            cells[colnum(cell.attrib["r"])] = shared[int(text)] if cell.attrib.get("t") == "s" and text else text
        rows.append([cells.get(i, "") for i in range(1, max(cells or {1: 1}) + 1)])
    return rows


def end_date(rows: list[list[str]]) -> str:
    text = " ".join(str(v) for row in rows[:20] for v in row)
    match = re.search(r"to\s+(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else ""


def statement_rows(sheet: str, rows: list[list[str]]) -> list[dict[str, str]]:
    out, d = [], end_date(rows)
    for row in rows:
        vals = [str(v).strip() for v in row if str(v).strip()]
        if len(vals) == 2 and vals[0].endswith("- Z"):
            out.append({"date": d, "symbol": vals[0], "charges": vals[1], "segment": sheet})
    for idx, row in enumerate(rows):
        vals = [str(v).strip() for v in row]
        if "Symbol" in vals and "Realized P&L" in vals:
            sym_i, pnl_i = vals.index("Symbol"), vals.index("Realized P&L")
            for data in rows[idx + 1:]:
                if len(data) > max(sym_i, pnl_i) and str(data[sym_i]).strip():
                    out.append({"date": d, "symbol": str(data[sym_i]).strip(), "realized_pnl": str(data[pnl_i]), "segment": sheet})
    return out


async def import_pnl_xlsx(pool: asyncpg.Pool, account_id: str, b64: str):
    with zipfile.ZipFile(BytesIO(base64.b64decode(b64))) as z:
        shared = strings(z)
        rows = [r for name, path in sheet_paths(z) for r in statement_rows(name, read_sheet(z, path, shared))]
    return await import_pnl_rows(pool, account_id, rows)
