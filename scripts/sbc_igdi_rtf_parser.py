#!/usr/bin/env python3
"""
Парсер СБЦ ИГДИ 2004 (RTF) -> генерация миграций 017/018/019
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
RTF_PATH = ROOT / "СБЦ Инженерно-геодезические изыскания.rtf"
TXT_PATH = Path("/tmp/sbc_igdi_2004.txt")

MIG_017 = ROOT / "migrations/017_sbc_igdi_2004_full_items.sql"
MIG_018 = ROOT / "migrations/018_sbc_igdi_2004_coeffs_and_rules.sql"
MIG_019 = ROOT / "migrations/019_sbc_igdi_2004_appendices.sql"

BOX_CHARS = set("─┬┼┴┐┌┘└")

DESCRIPTOR_KEYWORDS = [
    "масштаб",
    "категор",
    "высот",
    "сечен",
    "длина",
    "ширин",
    "глубин",
    "радиус",
    "диаметр",
    "площад",
    "расстоя",
    "протяж",
    "кол-",
    "колич",
    "стоимость полевых",
    "стоимость работ",
    "сметная стоимость",
    "длина трассы",
    "протяженность",
    "координат",
    "отметок",
]


@dataclass
class NormItem:
    table_no: int
    section: Optional[str]
    work_title: str
    unit: str
    price: Optional[float]
    price_field: Optional[float]
    price_office: Optional[float]
    params: Dict
    source_ref: Dict


@dataclass
class NormCoeff:
    code: str
    name: str
    value: float
    apply_to: str
    exclusive_group: Optional[str]
    conditions: Dict
    source_ref: Dict


@dataclass
class NormAddon:
    code: str
    name: str
    calc_type: str
    value: float
    unit: str
    base_type: str
    conditions: Dict
    source_ref: Dict


def run_textutil(rtf_path: Path, txt_path: Path) -> None:
    if not rtf_path.exists():
        raise FileNotFoundError(f"RTF not found: {rtf_path}")
    subprocess.run(
        ["textutil", "-convert", "txt", str(rtf_path), "-output", str(txt_path)],
        check=True,
    )


def read_text() -> str:
    if not TXT_PATH.exists():
        run_textutil(RTF_PATH, TXT_PATH)
    return TXT_PATH.read_text(errors="ignore")


def extract_table_title(text: str, table_start: int) -> Optional[str]:
    context = text[:table_start].splitlines()[-50:]
    keywords = ["Цены на", "Стоимость", "Создание", "Определение", "Базовые цены", "Укрупненные базовые цены"]
    for line in reversed(context):
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("примечание"):
            continue
        if any(k in line for k in keywords):
            line = re.sub(r"^\d+[\.\)]\s*", "", line)
            line = re.sub(r"\s+приводятся в таблице.*", "", line, flags=re.IGNORECASE)
            line = re.sub(r"\s+определяется.*", "", line, flags=re.IGNORECASE)
            line = re.sub(r"\s+указаны в таблице.*", "", line, flags=re.IGNORECASE)
            line = re.sub(r"^(Цены на|Стоимость)\s+", "", line, flags=re.IGNORECASE)
            line = re.sub(r"\s+в масштабах\s+1:\d+\s*-\s*1:\d+.*", "", line, flags=re.IGNORECASE)
            line = line.rstrip(".")
            line = line.strip()
            if line:
                line = line[0].upper() + line[1:]
            return line
    return None


def iter_tables(text: str):
    matches = list(re.finditer(r"\nТаблица\s+(\d+)\s*\n", text))
    for i, m in enumerate(matches):
        no = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = extract_table_title(text, m.start())
        yield no, text[start:end], title


def find_table_block(text: str, no: int) -> Optional[str]:
    m = re.search(rf"\nТаблица\s+{no}\s*\n", text)
    if not m:
        return None
    start = m.end()
    m2 = re.search(r"\nТаблица\s+\d+\s*\n", text[start:])
    end = start + m2.start() if m2 else len(text)
    return text[start:end]

def find_appendix_block(text: str, appendix_no: int) -> Optional[str]:
    m = re.search(rf"Приложение\s+{appendix_no}", text)
    if not m:
        return None
    start = m.start()
    m2 = re.search(r"Приложение\s+\d+\b", text[start + 20 :])
    end = start + 20 + m2.start() if m2 else len(text)
    return text[start:end]


def parse_unit(block: str) -> Optional[str]:
    for line in block.splitlines():
        if "Измеритель" in line:
            m = re.search(r"Измеритель\s*-\s*(.+)", line)
            if m:
                return m.group(1).strip()
    return None


def is_separator_text(s: str) -> bool:
    if not s:
        return True
    stripped = "".join(ch for ch in s if ch not in BOX_CHARS)
    return stripped.strip() == ""


def has_formula_markers(s: str) -> bool:
    if not s:
        return False
    return any(x in s for x in ["%", "+", "от", "более", "стоим"])


def is_number(s: str) -> bool:
    if not s:
        return False
    s = s.strip()
    if not s:
        return False
    if has_formula_markers(s.lower()):
        return False
    if re.fullmatch(r"[\-–—]+", s):
        return False
    if not re.search(r"\d", s):
        return False
    if re.search(r"[A-Za-zА-Яа-я]", s):
        return False
    return bool(re.fullmatch(r"[\d\s.,\-–—]+", s))


def to_number(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.strip()
    if has_formula_markers(s.lower()):
        return None
    if not re.search(r"\d", s):
        return None
    if re.search(r"[A-Za-zА-Яа-я]", s):
        return None
    s = re.sub(r"[^0-9,.-]", "", s)
    if s in ("", "-", "--"):
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def normalize_header_parts(parts: List[str]) -> str:
    text = ""
    for part in parts:
        part = part.strip()
        if not part or is_separator_text(part):
            continue
        if text.endswith("-"):
            text = text[:-1] + part
        else:
            text = (text + " " + part).strip()
    return re.sub(r"\s+", " ", text).strip()


def parse_table(block: str):
    lines = [l for l in block.splitlines()]
    try:
        box_start = next(i for i, l in enumerate(lines) if "┌" in l)
    except StopIteration:
        return None
    try:
        box_end = next(i for i, l in enumerate(lines[box_start:], start=box_start) if "┘" in l)
    except StopIteration:
        box_end = len(lines)
    box_lines = lines[box_start : box_end + 1]
    first_row = next(l for l in box_lines if l.startswith("│"))
    positions = [i for i, ch in enumerate(first_row) if ch == "│"]
    if len(positions) < 2:
        return None

    def split_outer(line: str) -> List[str]:
        return [line[positions[i] + 1 : positions[i + 1]].rstrip() for i in range(len(positions) - 1)]

    rows = [split_outer(l) for l in box_lines if l.startswith("│")]

    header_rows = []
    for r in rows:
        if r[0].strip().isdigit():
            break
        header_rows.append(r)
    if not header_rows:
        header_rows = [rows[0]]

    # determine subcolumn counts by max split in header rows
    subheaders = []
    for col in range(len(header_rows[0])):
        max_sub = max(len(hr[col].split("│")) for hr in header_rows)
        sub_parts = [[] for _ in range(max_sub)]
        for hr in header_rows:
            parts = [p.strip() for p in hr[col].split("│")]
            if max_sub > 1 and len(parts) == 1:
                continue
            if len(parts) < max_sub:
                parts = parts + [""] * (max_sub - len(parts))
            for i, p in enumerate(parts[:max_sub]):
                sub_parts[i].append(p)
        labels = [normalize_header_parts(p) for p in sub_parts]
        subheaders.append(labels)

    # groups
    groups = []
    current = []
    for line in box_lines:
        if line.startswith("├") or line.startswith("└"):
            if current:
                groups.append(current)
                current = []
            continue
        if line.startswith("│"):
            current.append(split_outer(line))
    if current:
        groups.append(current)

    # numeric columns
    num_cols = [[False for _ in subs] for subs in subheaders]
    for g in groups:
        for line in g:
            for ci, cell in enumerate(line):
                parts = [p.strip() for p in cell.split("│")]
                if len(parts) < len(subheaders[ci]):
                    parts = parts + [""] * (len(subheaders[ci]) - len(parts))
                for si, p in enumerate(parts[: len(subheaders[ci])]):
                    if ci == 0:
                        continue
                    if is_number(p):
                        num_cols[ci][si] = True
    num_cols[0] = [False for _ in num_cols[0]]
    # suppress descriptor-like numeric columns
    for ci, subs in enumerate(subheaders):
        for si, label in enumerate(subs):
            if not num_cols[ci][si]:
                continue
            l = label.lower()
            if any(k in l for k in DESCRIPTOR_KEYWORDS):
                num_cols[ci][si] = False

    return {"subheaders": subheaders, "groups": groups, "num_cols": num_cols}


def build_items(table_no: int, block: str, table_title: Optional[str] = None) -> List[NormItem]:
    unit = parse_unit(block)
    parsed = parse_table(block)
    if not parsed:
        return []

    subheaders = parsed["subheaders"]
    groups = parsed["groups"]
    num_cols = parsed["num_cols"]

    items: List[NormItem] = []
    last_descriptor: Optional[str] = None

    unit_col_idx = None
    price_col_idx = None
    if unit is None:
        for ci, subs in enumerate(subheaders):
            header = " ".join(subs).lower()
            if "измеритель" in header:
                unit_col_idx = ci
            if "цена" in header or "стоимость" in header:
                price_col_idx = ci
        if unit_col_idx is None or price_col_idx is None:
            return []

    for g in groups:
        col_lines = []
        for ci in range(len(subheaders)):
            col_lines.append([ln[ci] for ln in g])
        sec_candidate = " ".join([ln[0].strip() for ln in g if ln[0].strip()])
        m = re.search(r"\d+", sec_candidate)
        section = m.group(0) if m else None

        descriptor_parts = []
        for ci, subs in enumerate(subheaders):
            if ci == 0:
                continue
            if ci == unit_col_idx:
                continue
            if any(num_cols[ci]):
                continue
            text = " ".join([t.strip() for t in col_lines[ci] if t.strip()])
            if text:
                descriptor_parts.append(text)
        descriptor = " ".join(descriptor_parts).strip()
        if descriptor:
            if descriptor.lower().startswith("то же") and last_descriptor:
                tail = descriptor[5:].strip(" .:-–—")
                descriptor = f"{last_descriptor} {tail}".strip() if tail else last_descriptor
            else:
                last_descriptor = descriptor
        elif last_descriptor:
            descriptor = last_descriptor

        if unit is None:
            unit_text = " ".join([t.strip() for t in col_lines[unit_col_idx] if t.strip()])
            unit_value = unit_text or "ед."
            values = []
            for line in g:
                parts = [p.strip() for p in line[price_col_idx].split("│")]
                val = parts[0] if parts else ""
                if re.fullmatch(r"[\-–—\s]+", val):
                    continue
                if val.strip():
                    values.append(val.strip())
            nums = [to_number(v) for v in values if to_number(v) is not None]
            if not nums:
                continue
            price = nums[0]
            work_title = descriptor if descriptor else unit_text
            if table_title and (re.match(r"^1:\d+", work_title) or re.match(r"^\d+[\.,]?\d*", work_title)):
                work_title = f"{table_title} - {work_title}"
            items.append(
                NormItem(
                    table_no=table_no,
                    section=section,
                    work_title=work_title,
                    unit=unit_value,
                    price=price,
                    price_field=None,
                    price_office=None,
                    params={"descriptor": descriptor} if descriptor else {},
                    source_ref={"table": table_no, **({"row": section} if section else {})},
                )
            )
            continue

        # normal unit
        for ci, subs in enumerate(subheaders):
            for si, sub in enumerate(subs):
                if not num_cols[ci][si]:
                    continue
                if sub.strip() == "§":
                    continue
                values = []
                for line in g:
                    parts = [p.strip() for p in line[ci].split("│")]
                    if len(parts) < len(subs):
                        parts = parts + [""] * (len(subs) - len(parts))
                    val = parts[si]
                    if re.fullmatch(r"[\-–—\s]+", val):
                        continue
                    if val.strip():
                        values.append(val.strip())
                nums = [to_number(v) for v in values if to_number(v) is not None]
                if not nums:
                    continue
                price_field = None
                price_office = None
                price = None
                if len(nums) >= 2:
                    price_field = nums[0]
                    price_office = nums[1]
                else:
                    price = nums[0]

                header = sub.strip()
                title_parts = []
                if descriptor:
                    title_parts.append(descriptor)
                if header:
                    if re.fullmatch(r"[IVX]+", header):
                        title_parts.append(f"кат. {header}")
                    else:
                        title_parts.append(header)
                work_title = " - ".join(title_parts) if title_parts else header or descriptor
                if table_title and (re.match(r"^1:\d+", work_title) or re.match(r"^\d+[\.,]?\d*", work_title)):
                    work_title = f"{table_title} - {work_title}"
                params = {}
                if descriptor:
                    params["descriptor"] = descriptor
                if table_title:
                    params["table_title"] = table_title
                if header:
                    params["column"] = header
                if header and re.fullmatch(r"[IVX]+", header):
                    params["category"] = header
                # Масштаб: приоритет за дескриптором строки (табличной), а не за заголовком таблицы
                scale_match = re.search(r"1:\s?\d+", descriptor)
                if scale_match:
                    params["scale"] = scale_match.group(0).replace(" ", "")
                else:
                    scale_match = re.search(r"1:\s?\d+", work_title)
                    if scale_match:
                        params["scale"] = scale_match.group(0).replace(" ", "")
                if table_no == 9:
                    # Для табл.9: категория сложности в дескрипторе (римские цифры)
                    if "category" not in params:
                        mcat = re.search(r"\\b([IVX]+)\\b", descriptor)
                        if mcat:
                            params["category"] = mcat.group(1)
                    # Для табл.9: сечение рельефа — последнее число после масштаба
                    if "height_section" not in params and "scale" in params:
                        desc_no_scale = re.sub(r"1:\\s?\\d+", " ", descriptor)
                        nums = re.findall(r"\\d+[\\.,]?\\d*", desc_no_scale)
                        if nums:
                            try:
                                params["height_section"] = float(nums[-1].replace(",", "."))
                            except Exception:
                                pass
                    # Территория из колонки
                    if header:
                        h = header.lower()
                        if "незастро" in h:
                            params["territory"] = "незастроенная"
                        elif "застро" in h:
                            params["territory"] = "застроенная"
                        elif "пром" in h or "предприят" in h:
                            params["territory"] = "промпредприятие"

                source_ref = {"table": table_no}
                if section:
                    source_ref["row"] = section

                items.append(
                    NormItem(
                        table_no=table_no,
                        section=section,
                        work_title=work_title.strip(" -"),
                        unit=unit,
                        price=price,
                        price_field=price_field,
                        price_office=price_office,
                        params=params,
                        source_ref=source_ref,
                    )
                )

    return items


def parse_range(text: str) -> Tuple[Optional[float], Optional[float]]:
    if not text:
        return (None, None)
    t = text.lower().replace('"', ' ')
    t = t.replace("св.", "свыше")
    nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+[\.,]?\d*", t)]
    if "свыше" in t and "до" in t and len(nums) >= 2:
        return (nums[0], nums[1])
    if ("до" in t or "по" in t) and len(nums) >= 1 and "свыше" not in t:
        return (None, nums[0])
    if "свыше" in t and len(nums) >= 1 and "до" not in t:
        return (nums[0], None)
    if len(nums) == 2:
        return (nums[0], nums[1])
    if len(nums) == 1:
        return (None, nums[0])
    return (None, None)


def to_float(s: str) -> Optional[float]:
    if not s:
        return None
    m = re.search(r"\d+[\.,]?\d*", s)
    if not m:
        return None
    return float(m.group(0).replace(",", "."))


def build_coeffs_and_addons(text: str) -> Tuple[List[NormCoeff], List[NormAddon]]:
    coeffs: List[NormCoeff] = []
    addons: List[NormAddon] = []

    # OУ coefficients
    coeffs += [
        NormCoeff("MOUNTAIN_1500_1700", "Горные/высокогорные районы 1500-1700 м", 1.10, "field", "MOUNTAIN", {"altitude_min": 1500, "altitude_max": 1700}, {"table": 1, "section": "п.8а"}),
        NormCoeff("MOUNTAIN_1700_2000", "Горные/высокогорные районы 1700-2000 м", 1.15, "field", "MOUNTAIN", {"altitude_min": 1700, "altitude_max": 2000}, {"table": 1, "section": "п.8а"}),
        NormCoeff("MOUNTAIN_2000_3000", "Горные/высокогорные районы 2000-3000 м", 1.20, "field", "MOUNTAIN", {"altitude_min": 2000, "altitude_max": 3000}, {"table": 1, "section": "п.8а"}),
        NormCoeff("MOUNTAIN_OVER_3000", "Горные/высокогорные районы свыше 3000 м", 1.25, "field", "MOUNTAIN", {"altitude_min": 3000}, {"table": 1, "section": "п.8а"}),
        NormCoeff("SEASONAL_4_5_5", "Неблагоприятный период 4-5.5 мес", 1.20, "field", "SEASONAL", {"unfavorable_months_min": 4.0, "unfavorable_months_max": 5.5}, {"table": 2, "section": "п.8г"}),
        NormCoeff("SEASONAL_6_7_5", "Неблагоприятный период 6-7.5 мес", 1.30, "field", "SEASONAL", {"unfavorable_months_min": 6.0, "unfavorable_months_max": 7.5}, {"table": 2, "section": "п.8г"}),
        NormCoeff("SEASONAL_8_9_5", "Неблагоприятный период 8-9.5 мес", 1.40, "field", "SEASONAL", {"unfavorable_months_min": 8.0, "unfavorable_months_max": 9.5}, {"table": 2, "section": "п.8г"}),
    ]

    regional_map = [(1.1, 1.05), (1.15, 1.08), (1.2, 1.10), (1.25, 1.13), (1.3, 1.15), (1.4, 1.20), (1.5, 1.25), (1.6, 1.30), (1.7, 1.35), (1.8, 1.40), (1.9, 1.45), (2.0, 1.50)]
    for salary, estimate in regional_map:
        coeffs.append(
            NormCoeff(
                f"REGIONAL_{str(salary).replace('.', '_')}",
                f"Районный коэффициент к итогу сметной стоимости (зп {salary})",
                estimate,
                "total",
                "REGIONAL",
                {"salary_coeff": salary, "estimate_coeff": estimate},
                {"table": 3, "section": "п.8д"},
            )
        )

    coeffs += [
        NormCoeff("SPECIAL_REGIME_1_25", "Спецрежим территории", 1.25, "field", None, {"special_regime": True}, {"section": "п.8в"}),
        NormCoeff("RADIOACTIVITY_1_25", "Радиоактивность >1 мЗв/год (нижний уровень)", 1.25, "field", None, {"radioactivity_msv_per_year_min": 1.0, "radioactivity_coeff_range": "1.25-1.5"}, {"section": "п.8в"}),
        NormCoeff("RADIOACTIVITY_1_5", "Радиоактивность (верхний уровень)", 1.50, "field", None, {"radioactivity_msv_per_year_min": 1.0, "radioactivity_coeff_range": "1.25-1.5"}, {"section": "п.8в"}),
        NormCoeff("NIGHT_WORK_1_35", "Ночные работы (22:00-06:00)", 1.35, "field", None, {"night_work": True}, {"section": "п.8в"}),
        NormCoeff("FAR_NORTH_1_5", "Крайний Север", 1.50, "total", "FAR_NORTH", {"region_type": "far_north"}, {"section": "п.8е"}),
        NormCoeff("FAR_NORTH_EQUIV_1_25", "Приравненные к Крайнему Северу", 1.25, "total", "FAR_NORTH", {"region_type": "far_north_equivalent"}, {"section": "п.8е"}),
        NormCoeff("SOUTH_SIBERIA_FAREAST_1_15", "Южные районы Сибири/ДВ и др.", 1.15, "total", "FAR_NORTH", {"region_type": "south_regions"}, {"section": "п.8е"}),
        NormCoeff("FIELD_NO_ALLOWANCE_0_85", "Полевые без полевого довольствия/командировочных", 0.85, "field", None, {"no_field_allowance": True}, {"section": "п.14"}),
        NormCoeff("OFFICE_FIELD_CAMP_1_15", "Камеральные в экспедиционных условиях", 1.15, "office", None, {"office_in_field_camp": True}, {"section": "п.14"}),
        NormCoeff("INTERMEDIATE_MATERIALS_1_1", "Выдача промежуточных материалов", 1.10, "total", None, {"intermediate_materials": True}, {"section": "п.15а"}),
        NormCoeff("RESTRICTED_MATERIALS_1_1", "Камеральные с материалами ограниченного пользования", 1.10, "office", None, {"restricted_materials": True}, {"section": "п.15б"}),
        NormCoeff("FIELD_ARTIFICIAL_LIGHT_1_15", "Полевые с искусственным освещением", 1.15, "field", None, {"artificial_light": True}, {"section": "п.15в"}),
        NormCoeff("COLOR_PLAN_1_1", "План в цвете (камер.)", 1.10, "office", "COLOR_OR_COMPUTER", {"color_plan": True}, {"section": "п.15г"}),
        NormCoeff("COMPUTER_TECH_1_2", "Компьютерные технологии (камер.)", 1.20, "office", "COLOR_OR_COMPUTER", {"computer_tech": True}, {"section": "п.15д"}),
        NormCoeff("DUAL_MEDIA_1_75", "Два вида носителей (камер.)", 1.75, "office", "DUAL_MEDIA", {"dual_media": True}, {"section": "п.15е"}),
    ]

    # Table 9 notes
    coeffs += [
        NormCoeff("T9_SCALE_1_200", "Топоплан 1:200 (коэф. к §1-6 табл.9)", 2.0, "price", None, {"table_no": 9, "scale": "1:200"}, {"table": 9, "note": 1}),
        NormCoeff("T9_SCALE_1_500_HS_0_1", "Топоплан 1:500, сечение 0.1 м (коэф.)", 1.2, "price", None, {"table_no": 9, "scale": "1:500", "height_section": 0.1}, {"table": 9, "note": 2}),
        NormCoeff("T9_UPDATE_0_5", "Обновление инженерно-топографических планов", 0.5, "price", None, {"table_no": 9, "update_mode": True}, {"table": 9, "note": 3}),
        NormCoeff("T9_LARGE_STATIONS_1_2", "Крупные ж/д станции и внеклассные аэропорты", 1.2, "price", None, {"table_no": 9, "special_object": "large_station_or_airport"}, {"table": 9, "note": 5}),
        NormCoeff("T9_UNDERGROUND_UNBUILT_1_2", "Подземные коммуникации (незастроенная)", 1.2, "price", None, {"table_no": 9, "has_underground_comms": True, "territory": "незастроенная"}, {"table": 9, "note": 4}),
        NormCoeff("T9_UNDERGROUND_BUILT_1_55", "Подземные коммуникации (застроенная)", 1.55, "price", None, {"table_no": 9, "has_underground_comms": True, "territory": "застроенная"}, {"table": 9, "note": 4}),
        NormCoeff("T9_UNDERGROUND_INDUSTRIAL_1_75", "Подземные коммуникации (промпредприятие)", 1.75, "price", None, {"table_no": 9, "has_underground_comms": True, "territory": "промпредприятие"}, {"table": 9, "note": 4}),
        NormCoeff("T9_DETAILED_WELLS_1_3", "Детальное обследование колодцев и надземных коммуникаций", 1.3, "price", None, {"table_no": 9, "has_detailed_wells_sketches": True}, {"table": 9, "note": 5}),
        NormCoeff("T9_OBMERNYE_1_1", "Обмерные чертежи зданий и сооружений", 1.1, "price", None, {"table_no": 9, "measurement_drawings": True}, {"table": 9, "note": 5}),
        NormCoeff("T9_RED_LINES_1_15", "Красные линии (камер.)", 1.15, "office", None, {"table_no": 9, "red_lines": True, "analytic_coords": False}, {"table": 9, "note": 6}),
        NormCoeff("T9_RED_LINES_1_30", "Красные линии с аналитическим расчетом", 1.30, "office", None, {"table_no": 9, "red_lines": True, "analytic_coords": True}, {"table": 9, "note": 6}),
        NormCoeff("T9_TREE_SURVEY_0_7", "Подеревная съемка (коэф.)", 0.7, "price", None, {"table_no": 9, "tree_survey": True}, {"table": 9, "note": 5}),
    ]

    # Спутниковые системы для плановых опорных сетей (табл.8, примечание)
    coeffs += [
        NormCoeff(
            "T8_SATELLITE_1_3",
            "Плановые опорные сети с применением спутниковых систем",
            1.30,
            "price",
            None,
            {"table_no": 8, "use_satellite": True},
            {"table": 8, "note": 2},
        )
    ]

    # Таблица 8, примечание 1: без закладки центров/реперов (только полевые)
    coeffs += [
        NormCoeff(
            "T8_NO_CENTER_0_7",
            "Измерения без закладки центров (плановые сети §§1-3)",
            0.70,
            "field",
            None,
            {"table_no": 8, "section_min": 1, "section_max": 3, "no_center": True},
            {"table": 8, "note": 1},
        ),
        NormCoeff(
            "T8_NO_CENTER_0_4",
            "Измерения без закладки центров (высотные сети §4)",
            0.40,
            "field",
            None,
            {"table_no": 8, "section": 4, "no_center": True},
            {"table": 8, "note": 1},
        ),
    ]

    # Vertical survey
    coeffs += [
        NormCoeff("T9_VERTICAL_BUILT_1_500_FIELD", "Вертикальная съемка (застр., 1:500) полевые", 0.40, "field", None, {"table_no": 9, "vertical_survey": True, "territory": "застроенная", "scale": "1:500"}, {"table": 9, "note": "вертикальная"}),
        NormCoeff("T9_VERTICAL_BUILT_1_500_OFFICE", "Вертикальная съемка (застр., 1:500) камеральные", 0.55, "office", None, {"table_no": 9, "vertical_survey": True, "territory": "застроенная", "scale": "1:500"}, {"table": 9, "note": "вертикальная"}),
        NormCoeff("T9_VERTICAL_BUILT_1_1000_FIELD", "Вертикальная съемка (застр., 1:1000) полевые", 0.30, "field", None, {"table_no": 9, "vertical_survey": True, "territory": "застроенная", "scale": "1:1000"}, {"table": 9, "note": "вертикальная"}),
        NormCoeff("T9_VERTICAL_BUILT_1_1000_OFFICE", "Вертикальная съемка (застр., 1:1000) камеральные", 0.45, "office", None, {"table_no": 9, "vertical_survey": True, "territory": "застроенная", "scale": "1:1000"}, {"table": 9, "note": "вертикальная"}),
        NormCoeff("T9_VERTICAL_BUILT_1_2000_10000_FIELD", "Вертикальная съемка (застр., 1:2000-1:10000) полевые", 0.25, "field", None, {"table_no": 9, "vertical_survey": True, "territory": "застроенная", "scale_min": "1:2000", "scale_max": "1:10000"}, {"table": 9, "note": "вертикальная"}),
        NormCoeff("T9_VERTICAL_BUILT_1_2000_10000_OFFICE", "Вертикальная съемка (застр., 1:2000-1:10000) камеральные", 0.40, "office", None, {"table_no": 9, "vertical_survey": True, "territory": "застроенная", "scale_min": "1:2000", "scale_max": "1:10000"}, {"table": 9, "note": "вертикальная"}),
        NormCoeff("T9_VERTICAL_INDUSTRIAL_1_500_FIELD", "Вертикальная съемка (промпредпр., 1:500) полевые", 0.30, "field", None, {"table_no": 9, "vertical_survey": True, "territory": "промпредприятие", "scale": "1:500"}, {"table": 9, "note": "вертикальная"}),
        NormCoeff("T9_VERTICAL_INDUSTRIAL_1_500_OFFICE", "Вертикальная съемка (промпредпр., 1:500) камеральные", 0.50, "office", None, {"table_no": 9, "vertical_survey": True, "territory": "промпредприятие", "scale": "1:500"}, {"table": 9, "note": "вертикальная"}),
        NormCoeff("T9_VERTICAL_INDUSTRIAL_1_1000_10000_FIELD", "Вертикальная съемка (промпредпр., 1:1000-1:10000) полевые", 0.25, "field", None, {"table_no": 9, "vertical_survey": True, "territory": "промпредприятие", "scale_min": "1:1000", "scale_max": "1:10000"}, {"table": 9, "note": "вертикальная"}),
        NormCoeff("T9_VERTICAL_INDUSTRIAL_1_1000_10000_OFFICE", "Вертикальная съемка (промпредпр., 1:1000-1:10000) камеральные", 0.40, "office", None, {"table_no": 9, "vertical_survey": True, "territory": "промпредприятие", "scale_min": "1:1000", "scale_max": "1:10000"}, {"table": 9, "note": "вертикальная"}),
    ]

    # Table 4 internal transport
    block4 = find_table_block(text, 4)
    if block4:
        lines = block4.splitlines()
        header_idx = next((i for i, l in enumerate(lines) if "до 75" in l), None)
        col_labels: List[str] = []
        if header_idx is not None:
            line1 = lines[header_idx]
            line2 = lines[header_idx + 1] if header_idx + 1 < len(lines) else ""
            cells1 = [c.strip() for c in line1.strip("│").split("│")]
            cells2 = [c.strip() for c in line2.strip("│").split("│")]
            for i in range(2, len(cells1)):
                part1 = cells1[i]
                part2 = cells2[i] if i < len(cells2) else ""
                col_labels.append((part1 + " " + part2).strip())

        for line in lines:
            if re.match(r"^│\d+\s*│", line):
                cells = [c.strip() for c in line.strip("│").split("│")]
                row_label = cells[1]
                rmin, rmax = parse_range(row_label)
                for idx, val_text in enumerate(cells[2:]):
                    val = to_float(val_text)
                    if val is None:
                        continue
                    col_label = col_labels[idx] if idx < len(col_labels) else ""
                    cmin, cmax = parse_range(col_label)
                    addons.append(
                        NormAddon(
                            code=f"INTERNAL_T4_{rmin}_{rmax}_{cmin}_{cmax}",
                            name=f"Внутренний транспорт: {row_label}, стоимость полевых {col_label}",
                            calc_type="percent",
                            value=val / 100.0,
                            unit="%",
                            base_type="field",
                            conditions={
                                "distance_from_base_km_min": rmin,
                                "distance_from_base_km_max": rmax,
                                "field_cost_thousand_min": cmin,
                                "field_cost_thousand_max": cmax,
                            },
                            source_ref={"table": 4},
                        )
                    )

    # Table 5 external transport
    block5 = find_table_block(text, 5)
    if block5:
        lines = block5.splitlines()
        header_idx = next((i for i, l in enumerate(lines) if "до 1" in l and "12" in l), None)
        col_labels: List[str] = []
        if header_idx is not None:
            line1 = lines[header_idx]
            line2 = lines[header_idx + 1] if header_idx + 1 < len(lines) else ""
            cells1 = [c.strip() for c in line1.strip("│").split("│")]
            cells2 = [c.strip() for c in line2.strip("│").split("│")]
            for i in range(2, len(cells1)):
                part1 = cells1[i]
                part2 = cells2[i] if i < len(cells2) else ""
                col_labels.append((part1 + " " + part2).strip())

        for line in lines:
            if re.match(r"^│\d+\s*│", line):
                cells = [c.strip() for c in line.strip("│").split("│")]
                row_label = cells[1]
                rmin, rmax = parse_range(row_label)
                for idx, val_text in enumerate(cells[2:]):
                    val = to_float(val_text)
                    if val is None:
                        continue
                    col_label = col_labels[idx] if idx < len(col_labels) else ""
                    dmin, dmax = parse_range(col_label)
                    addons.append(
                        NormAddon(
                            code=f"EXTERNAL_T5_{rmin}_{rmax}_{dmin}_{dmax}",
                            name=f"Внешний транспорт: {row_label}, длит. {col_label}",
                            calc_type="percent",
                            value=val / 100.0,
                            unit="%",
                            base_type="field_plus_internal",
                            conditions={
                                "distance_oneway_km_min": rmin,
                                "distance_oneway_km_max": rmax,
                                "duration_months_min": dmin,
                                "duration_months_max": dmax,
                            },
                            source_ref={"table": 5},
                        )
                    )

    # Table 6 coefficients to org/liq
    block6 = find_table_block(text, 6)
    if block6:
        for line in block6.splitlines():
            if re.match(r"^│\d+\s*│", line):
                cells = [c.strip() for c in line.strip("│").split("│")]
                row_label = cells[1]
                rmin, rmax = parse_range(row_label)
                val = to_float(cells[2])
                if val is None:
                    continue
                coeffs.append(
                    NormCoeff(
                        code=f"ORG_LIQ_DURATION_{rmin}_{rmax}",
                        name=f"Коэф. к орг/ликв работ при длит. {row_label}",
                        value=val,
                        apply_to="total",
                        exclusive_group=None,
                        conditions={
                            "applies_to_addon": "ORG_LIQ_6PCT",
                            "duration_months_min": rmin,
                            "duration_months_max": rmax,
                        },
                        source_ref={"table": 6},
                    )
                )

    # Table 10 small areas
    block10 = find_table_block(text, 10)
    if block10:
        coeff_line = next((l for l in block10.splitlines() if "1,4" in l or "1.4" in l), None)
        coeff_vals: List[Optional[float]] = [None, None, None]
        if coeff_line:
            cells = [c.strip() for c in coeff_line.strip("│").split("│")]
            for i, cell in enumerate(cells[2:5]):
                coeff_vals[i] = to_float(cell)
        for line in block10.splitlines():
            if re.match(r"^│\d+\s*│", line):
                cells = [c.strip() for c in line.strip("│").split("│")]
                scale = cells[1]
                area1 = cells[2]
                area2 = cells[3]
                width = cells[4]
                if coeff_vals[0]:
                    amin, amax = parse_range(area1)
                    coeffs.append(NormCoeff(f"T10_AREA1_{scale}", f"Коэф. малых площадей ({scale}, {area1})", coeff_vals[0], "price", None, {"table_no": 9, "scale": scale, "area_min": amin, "area_max": amax}, {"table": 10}))
                if coeff_vals[1]:
                    amin, amax = parse_range(area2)
                    coeffs.append(NormCoeff(f"T10_AREA2_{scale}", f"Коэф. малых площадей ({scale}, {area2})", coeff_vals[1], "price", None, {"table_no": 9, "scale": scale, "area_min": amin, "area_max": amax}, {"table": 10}))
                if coeff_vals[2]:
                    wmin, wmax = parse_range(width)
                    coeffs.append(NormCoeff(f"T10_WIDTH_{scale}", f"Коэф. узких полос ({scale}, {width})", coeff_vals[2], "price", None, {"table_no": 9, "scale": scale, "strip_width_min": wmin, "strip_width_max": wmax}, {"table": 10}))

    # Tables 78/79/80 piecewise formulas
    def parse_piecewise_table(no: int, code_prefix: str, name_prefix: str, base_type: str) -> None:
        block = find_table_block(text, no)
        if not block:
            return
        for line in block.splitlines():
            if re.match(r"^│\d+\s*│", line):
                cells = [c.strip() for c in line.strip("│").split("│")]
                row_label = cells[1]
                price_text = cells[2]
                rmin, rmax = parse_range(row_label)
                perc = None
                m = re.search(r"(\d+[\.,]?\d*)\s*%", price_text)
                if m:
                    perc = float(m.group(1).replace(",", ".")) / 100.0
                fixed = to_float(price_text)
                addons.append(
                    NormAddon(
                        code=f"{code_prefix}_{rmin}_{rmax}",
                        name=f"{name_prefix}: {row_label}",
                        calc_type="percent",
                        value=perc if perc is not None else 0.0,
                        unit="%",
                        base_type=base_type,
                        conditions={
                            "base_cost_thousand_min": rmin,
                            "base_cost_thousand_max": rmax,
                            "fixed_amount": fixed,
                            "percent_over": perc,
                            "formula_text": price_text,
                        },
                        source_ref={"table": no},
                    )
                )

    parse_piecewise_table(78, "PROGRAM_T78", "Программа изысканий", "subtotal")
    parse_piecewise_table(79, "REPORT_T79", "Технический отчет", "subtotal")
    parse_piecewise_table(80, "REGISTRATION_T80", "Регистрация/приемка материалов", "subtotal")

    return coeffs, addons


def parse_appendices(text: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    desert_coeffs: List[Dict] = []
    unfavorable_periods: List[Dict] = []
    zone_lists: List[Dict] = []

    def iter_box_rows(block: str) -> List[List[str]]:
        lines = [l for l in block.splitlines()]
        try:
            box_start = next(i for i, l in enumerate(lines) if "┌" in l)
        except StopIteration:
            return []
        try:
            box_end = next(i for i, l in enumerate(lines[box_start:], start=box_start) if "┘" in l)
        except StopIteration:
            box_end = len(lines)
        box_lines = lines[box_start : box_end + 1]
        candidate_rows = [l for l in box_lines if l.startswith("│")]
        if not candidate_rows:
            return []
        widest_row = max(candidate_rows, key=lambda l: l.count("│"))
        positions = [i for i, ch in enumerate(widest_row) if ch == "│"]

        def split_outer(line: str) -> List[str]:
            return [line[positions[i] + 1 : positions[i + 1]].rstrip() for i in range(len(positions) - 1)]

        rows: List[List[str]] = []
        for line in box_lines:
            if line.startswith("│"):
                rows.append(split_outer(line))
        return rows

    def parse_box_groups(block: str) -> List[List[List[str]]]:
        lines = [l for l in block.splitlines()]
        try:
            box_start = next(i for i, l in enumerate(lines) if "┌" in l)
        except StopIteration:
            return []
        try:
            box_end = next(i for i, l in enumerate(lines[box_start:], start=box_start) if "┘" in l)
        except StopIteration:
            box_end = len(lines)
        box_lines = lines[box_start : box_end + 1]
        candidate_rows = [l for l in box_lines if l.startswith("│")]
        if not candidate_rows:
            return []
        widest_row = max(candidate_rows, key=lambda l: l.count("│"))
        positions = [i for i, ch in enumerate(widest_row) if ch == "│"]

        def split_outer(line: str) -> List[str]:
            return [line[positions[i] + 1 : positions[i + 1]].rstrip() for i in range(len(positions) - 1)]

        groups: List[List[List[str]]] = []
        current: List[List[str]] = []
        for line in box_lines:
            if line.startswith("├") or line.startswith("└"):
                if current:
                    groups.append(current)
                    current = []
                continue
            if line.startswith("│"):
                current.append(split_outer(line))
        if current:
            groups.append(current)
        return groups

    def join_wrapped(parts: List[str]) -> str:
        text = ""
        for part in parts:
            part = part.strip()
            if not part or is_separator_text(part):
                continue
            if text.endswith("-"):
                text = text[:-1] + part
            else:
                text = (text + " " + part).strip()
        return re.sub(r"\s+", " ", text).strip()

    def looks_like_region(name: str) -> bool:
        n = name.lower()
        return bool(re.search(r"\b(республика|область|край|округ|авт\.|автоном|город)\b", n))

    def is_subregion(name: str) -> bool:
        n = name.lower().strip()
        return n.startswith(("то же", "\"", "в горной", "в высокогорной", "между", "севернее", "южнее", "высокогорной", "в горной части", "в высокогорной части"))

    # Appendix 1: desert coefficients (table)
    app1 = find_appendix_block(text, 1)
    if app1:
        rows = iter_box_rows(app1)
        current_region = None
        current_subregion_parts: List[str] = []
        current_coeff: Optional[float] = None
        for row in rows:
            if len(row) < 2:
                continue
            name = row[0].strip()
            coeff_text = row[1].strip()
            if not name and not coeff_text:
                continue
            if name.lower().startswith("республики,") or "коэффициенты" in name.lower():
                continue
            coeff = to_float(coeff_text)
            if coeff is None:
                if name and looks_like_region(name) and len(name) <= 60:
                    if current_subregion_parts and current_coeff is not None:
                        full_name = join_wrapped(current_subregion_parts)
                        region_name = current_region or full_name
                        subregion = None if current_region is None else full_name
                        desert_coeffs.append(
                            {
                                "region_name": region_name,
                                "subregion_name": subregion,
                                "coeff": current_coeff,
                                "source_ref": {"appendix": 1},
                            }
                        )
                        current_subregion_parts = []
                        current_coeff = None
                    current_region = name.rstrip(":")
                    continue
                if current_subregion_parts:
                    current_subregion_parts.append(name)
                continue
            if current_subregion_parts and current_coeff is not None:
                full_name = join_wrapped(current_subregion_parts)
                region_name = current_region or full_name
                subregion = None if current_region is None else full_name
                desert_coeffs.append(
                    {
                        "region_name": region_name,
                        "subregion_name": subregion,
                        "coeff": current_coeff,
                        "source_ref": {"appendix": 1},
                    }
                )
            current_subregion_parts = [name] if name else []
            current_coeff = coeff
        if current_subregion_parts and current_coeff is not None:
            full_name = join_wrapped(current_subregion_parts)
            region_name = current_region or full_name
            subregion = None if current_region is None else full_name
            desert_coeffs.append(
                {
                    "region_name": region_name,
                    "subregion_name": subregion,
                    "coeff": current_coeff,
                    "source_ref": {"appendix": 1},
                }
            )

    # Appendix 2: unfavorable period table
    app2 = find_appendix_block(text, 2)
    if app2:
        rows = iter_box_rows(app2)
        current_region = None
        for row in rows:
            if len(row) < 4:
                continue
            name = row[0].strip()
            start = row[1].strip()
            end = row[2].strip()
            duration = to_float(row[3])
            if not name and not start and not end and duration is None:
                continue
            name_lower = name.lower()
            if name_lower in {"республики", "края", "области", "автономные округа"}:
                current_region = None
                continue
            if duration is None and not start and not end:
                if name_lower.startswith("республики, края") or name_lower.startswith("республики"):
                    continue
                if name:
                    if name.endswith(":") or looks_like_region(name) or current_region is None:
                        current_region = name.rstrip(":")
                    elif current_region and current_region.endswith("-"):
                        current_region = f"{current_region} {name}".strip()
                continue
            if duration is None:
                continue
            if current_region and is_subregion(name):
                region_name = f"{current_region} - {name}"
            else:
                region_name = name if name else (current_region or "")
            if looks_like_region(name):
                current_region = name
            unfavorable_periods.append(
                {
                    "region_name": region_name,
                    "period_start": start,
                    "period_end": end,
                    "duration_months": duration,
                    "source_ref": {"appendix": 2},
                }
            )

    # Appendix 3 & 4: salary coeff zones
    for app_no in (3, 4):
        m = re.search(rf"Приложение {app_no}", text)
        if not m:
            continue
        start = m.start()
        m2 = re.search(r"Приложение\s+\d+", text[start + 20 :])
        end = start + 20 + m2.start() if m2 else len(text)
        block = text[start:end]
        current_zone = None
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            header = re.match(r"\d+\.\s+Районы, где.*коэффициент\s+(\d+[\.,]?\d*)", line)
            if header:
                coeff = header.group(1).replace(",", ".")
                current_zone = f"salary_coeff_{coeff}"
                continue
            if current_zone and not line.startswith("-"):
                zone_lists.append(
                    {
                        "zone_type": current_zone,
                        "region_name": line,
                        "subregion_name": None,
                        "source_ref": {"appendix": app_no},
                    }
                )

    # Appendix 5: far north lists
    m = re.search(r"Приложение 5", text)
    if m:
        start = m.start()
        end = len(text)
        block = text[start:end]
        zone = None
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("районы крайнего севера"):
                zone = "far_north"
                continue
            if line.lower().startswith("местности, приравненные"):
                zone = "far_north_equivalent"
                continue
            if zone and not line.startswith("-"):
                zone_lists.append(
                    {
                        "zone_type": zone,
                        "region_name": line,
                        "subregion_name": None,
                        "source_ref": {"appendix": 5},
                    }
                )

    return desert_coeffs, unfavorable_periods, zone_lists


def write_017(items: List[NormItem]) -> None:
    lines = []
    lines.append("-- Миграция 017: Полная загрузка расценок СБЦ ИГДИ 2004 из RTF")
    lines.append("-- Источник: СБЦ Инженерно-геодезические изыскания (RTF)")
    lines.append("")
    lines.append("DO $$")
    lines.append("DECLARE")
    lines.append("    v_doc_id UUID;")
    lines.append("BEGIN")
    lines.append("    SELECT id INTO v_doc_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';")
    lines.append("    IF v_doc_id IS NULL THEN")
    lines.append("        INSERT INTO norm_docs (code, title, version, base_date, source_name)")
    lines.append("        VALUES ('SBC_IGDI_2004', 'СБЦ на инженерные изыскания для строительства. Инженерно-геодезические изыскания', '2004', '2001-01-01', 'RTF')")
    lines.append("        RETURNING id INTO v_doc_id;")
    lines.append("    END IF;")
    lines.append("")
    lines.append("    DELETE FROM norm_items WHERE doc_id = v_doc_id AND table_no BETWEEN 8 AND 84;")
    lines.append("")
    lines.append("    INSERT INTO norm_items (doc_id, table_no, section, work_title, unit, price, price_field, price_office, params, source_ref) VALUES")

    def q(s: Optional[str]) -> Optional[str]:
        return s.replace("'", "''") if s is not None else None

    values = []
    for item in items:
        params = json.dumps(item.params, ensure_ascii=False)
        source = dict(item.source_ref)
        source["source"] = "rtf_2004"
        source_json = json.dumps(source, ensure_ascii=False)
        values.append(
            "    (v_doc_id, {table_no}, {section}, '{work_title}', '{unit}', {price}, {price_field}, {price_office}, '{params}'::jsonb, '{source}'::jsonb)".format(
                table_no=item.table_no,
                section=("'%s'" % q(item.section) if item.section else "NULL"),
                work_title=q(item.work_title or ""),
                unit=q(item.unit or ""),
                price=("NULL" if item.price is None else f"{item.price:.2f}"),
                price_field=("NULL" if item.price_field is None else f"{item.price_field:.2f}"),
                price_office=("NULL" if item.price_office is None else f"{item.price_office:.2f}"),
                params=q(params),
                source=q(source_json),
            )
        )

    for i, v in enumerate(values):
        lines.append(v + ("," if i < len(values) - 1 else ";"))

    lines.append("")
    lines.append("    RAISE NOTICE 'Загружено расценок: %', (SELECT COUNT(*) FROM norm_items WHERE doc_id = v_doc_id AND (source_ref->>'source') = 'rtf_2004');")
    lines.append("END $$;")

    MIG_017.write_text("\n".join(lines), encoding="utf-8")


def write_018(coeffs: List[NormCoeff], addons: List[NormAddon]) -> None:
    lines = []
    lines.append("-- Миграция 018: Коэффициенты и надбавки СБЦ ИГДИ 2004 (ОУ, табл.1-6,10,78-80, примечания табл.9)")
    lines.append("DO $$")
    lines.append("DECLARE")
    lines.append("    v_doc_id UUID;")
    lines.append("BEGIN")
    lines.append("    SELECT id INTO v_doc_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';")
    lines.append("    IF v_doc_id IS NULL THEN")
    lines.append("        RAISE EXCEPTION 'Документ SBC_IGDI_2004 не найден. Сначала выполните миграцию 017.';")
    lines.append("    END IF;")
    lines.append("")
    lines.append("    DELETE FROM norm_coeffs WHERE doc_id = v_doc_id;")
    lines.append("    DELETE FROM norm_addons WHERE doc_id = v_doc_id;")
    lines.append("")

    def q(s: Optional[str]) -> Optional[str]:
        return s.replace("'", "''") if s is not None else None

    if coeffs:
        lines.append("    INSERT INTO norm_coeffs (doc_id, code, name, value, apply_to, exclusive_group, conditions, source_ref) VALUES")
        for i, c in enumerate(coeffs):
            ccond = json.dumps(c.conditions, ensure_ascii=False)
            sref = dict(c.source_ref)
            sref["source"] = "rtf_2004"
            sref_json = json.dumps(sref, ensure_ascii=False)
            lines.append(
                "    (v_doc_id, '{code}', '{name}', {value}, '{apply_to}', {exclusive_group}, '{conditions}'::jsonb, '{source}'::jsonb){comma}".format(
                    code=q(c.code),
                    name=q(c.name),
                    value=f"{c.value:.4f}",
                    apply_to=c.apply_to,
                    exclusive_group=("NULL" if not c.exclusive_group else f"'{q(c.exclusive_group)}'"),
                    conditions=q(ccond),
                    source=q(sref_json),
                    comma="," if i < len(coeffs) - 1 else ";",
                )
            )
        lines.append("")

    if addons:
        lines.append("    INSERT INTO norm_addons (doc_id, code, name, calc_type, value, unit, base_type, conditions, source_ref) VALUES")
        for i, a in enumerate(addons):
            acond = json.dumps(a.conditions, ensure_ascii=False)
            sref = dict(a.source_ref)
            sref["source"] = "rtf_2004"
            sref_json = json.dumps(sref, ensure_ascii=False)
            lines.append(
                "    (v_doc_id, '{code}', '{name}', '{calc_type}', {value}, '{unit}', '{base_type}', '{conditions}'::jsonb, '{source}'::jsonb){comma}".format(
                    code=q(a.code),
                    name=q(a.name),
                    calc_type=a.calc_type,
                    value=f"{a.value:.6f}",
                    unit=q(a.unit or ""),
                    base_type=a.base_type,
                    conditions=q(acond),
                    source=q(sref_json),
                    comma="," if i < len(addons) - 1 else ";",
                )
            )

    lines.append("")
    lines.append("    RAISE NOTICE 'Коэффициенты добавлены: %', (SELECT COUNT(*) FROM norm_coeffs WHERE doc_id = v_doc_id AND (source_ref->>'source') = 'rtf_2004');")
    lines.append("    RAISE NOTICE 'Надбавки добавлены: %', (SELECT COUNT(*) FROM norm_addons WHERE doc_id = v_doc_id AND (source_ref->>'source') = 'rtf_2004');")
    lines.append("END $$;")

    MIG_018.write_text("\n".join(lines), encoding="utf-8")


def write_019(desert: List[Dict], unfavorable: List[Dict], zones: List[Dict]) -> None:
    lines = []
    lines.append("-- Миграция 019: Приложения 1-5 (региональные коэффициенты и периоды)")
    lines.append("DO $$")
    lines.append("DECLARE")
    lines.append("    v_doc_id UUID;")
    lines.append("BEGIN")
    lines.append("    SELECT id INTO v_doc_id FROM norm_docs WHERE code = 'SBC_IGDI_2004';")
    lines.append("    IF v_doc_id IS NULL THEN")
    lines.append("        RAISE EXCEPTION 'Документ SBC_IGDI_2004 не найден. Сначала выполните миграцию 017.';")
    lines.append("    END IF;")
    lines.append("")
    lines.append("    CREATE TABLE IF NOT EXISTS regional_desert_coeffs (")
    lines.append("        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),")
    lines.append("        doc_id uuid NOT NULL REFERENCES norm_docs(id) ON DELETE CASCADE,")
    lines.append("        region_name text NOT NULL,")
    lines.append("        subregion_name text,")
    lines.append("        coeff numeric(8,4) NOT NULL,")
    lines.append("        source_ref jsonb DEFAULT '{}'::jsonb,")
    lines.append("        created_at timestamptz DEFAULT now(),")
    lines.append("        updated_at timestamptz DEFAULT now()")
    lines.append("    );")
    lines.append("")
    lines.append("    CREATE TABLE IF NOT EXISTS regional_unfavorable_periods (")
    lines.append("        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),")
    lines.append("        doc_id uuid NOT NULL REFERENCES norm_docs(id) ON DELETE CASCADE,")
    lines.append("        region_name text NOT NULL,")
    lines.append("        period_start text,")
    lines.append("        period_end text,")
    lines.append("        duration_months numeric(5,2) NOT NULL,")
    lines.append("        source_ref jsonb DEFAULT '{}'::jsonb,")
    lines.append("        created_at timestamptz DEFAULT now(),")
    lines.append("        updated_at timestamptz DEFAULT now()")
    lines.append("    );")
    lines.append("")
    lines.append("    CREATE TABLE IF NOT EXISTS regional_zone_lists (")
    lines.append("        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),")
    lines.append("        doc_id uuid NOT NULL REFERENCES norm_docs(id) ON DELETE CASCADE,")
    lines.append("        zone_type text NOT NULL,")
    lines.append("        region_name text NOT NULL,")
    lines.append("        subregion_name text,")
    lines.append("        source_ref jsonb DEFAULT '{}'::jsonb,")
    lines.append("        created_at timestamptz DEFAULT now(),")
    lines.append("        updated_at timestamptz DEFAULT now()")
    lines.append("    );")
    lines.append("")
    lines.append("    DELETE FROM regional_desert_coeffs WHERE doc_id = v_doc_id;")
    lines.append("    DELETE FROM regional_unfavorable_periods WHERE doc_id = v_doc_id;")
    lines.append("    DELETE FROM regional_zone_lists WHERE doc_id = v_doc_id;")
    lines.append("")

    def q(s: Optional[str]) -> Optional[str]:
        return s.replace("'", "''") if s is not None else None

    if desert:
        lines.append("    INSERT INTO regional_desert_coeffs (doc_id, region_name, subregion_name, coeff, source_ref) VALUES")
        for i, d in enumerate(desert):
            sref = dict(d.get("source_ref", {}))
            sref_json = json.dumps(sref, ensure_ascii=False)
            lines.append(
                "    (v_doc_id, '{region}', {sub}, {coeff}, '{source}'::jsonb){comma}".format(
                    region=q(d["region_name"]),
                    sub=("NULL" if not d.get("subregion_name") else f"'{q(d['subregion_name'])}'"),
                    coeff=f"{d['coeff']:.4f}",
                    source=q(sref_json),
                    comma="," if i < len(desert) - 1 else ";",
                )
            )
        lines.append("")

    if unfavorable:
        lines.append("    INSERT INTO regional_unfavorable_periods (doc_id, region_name, period_start, period_end, duration_months, source_ref) VALUES")
        for i, d in enumerate(unfavorable):
            sref = dict(d.get("source_ref", {}))
            sref_json = json.dumps(sref, ensure_ascii=False)
            lines.append(
                "    (v_doc_id, '{region}', '{start}', '{end}', {duration}, '{source}'::jsonb){comma}".format(
                    region=q(d["region_name"]),
                    start=q(d.get("period_start") or ""),
                    end=q(d.get("period_end") or ""),
                    duration=f"{d['duration_months']:.2f}",
                    source=q(sref_json),
                    comma="," if i < len(unfavorable) - 1 else ";",
                )
            )
        lines.append("")

    if zones:
        lines.append("    INSERT INTO regional_zone_lists (doc_id, zone_type, region_name, subregion_name, source_ref) VALUES")
        for i, d in enumerate(zones):
            sref = dict(d.get("source_ref", {}))
            sref_json = json.dumps(sref, ensure_ascii=False)
            lines.append(
                "    (v_doc_id, '{zone}', '{region}', {sub}, '{source}'::jsonb){comma}".format(
                    zone=q(d["zone_type"]),
                    region=q(d["region_name"]),
                    sub=("NULL" if not d.get("subregion_name") else f"'{q(d['subregion_name'])}'"),
                    source=q(sref_json),
                    comma="," if i < len(zones) - 1 else ";",
                )
            )

    lines.append("")
    lines.append("    RAISE NOTICE 'Приложения загружены.';")
    lines.append("END $$;")

    MIG_019.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    text = read_text()
    items: List[NormItem] = []
    for no, block, title in iter_tables(text):
        items.extend(build_items(no, block, title))

    coeffs, addons = build_coeffs_and_addons(text)
    desert, unfavorable, zones = parse_appendices(text)

    write_017(items)
    write_018(coeffs, addons)
    write_019(desert, unfavorable, zones)

    print(f"Generated: {MIG_017.name}, {MIG_018.name}, {MIG_019.name}")
    print(f"Items: {len(items)}, Coeffs: {len(coeffs)}, Addons: {len(addons)}")
    print(f"Appendix rows: desert={len(desert)}, unfavorable={len(unfavorable)}, zones={len(zones)}")


if __name__ == "__main__":
    main()
