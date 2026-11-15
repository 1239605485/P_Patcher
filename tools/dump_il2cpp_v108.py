"""Dump names, types, parameters, and method RVAs from Unity IL2CPP v108."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile


def table_layout(data: bytes, index: int) -> tuple[int, int, int]:
    header = struct.unpack_from("<125i", data, 0)
    offset, size, count = header[2 + index * 3 : 5 + index * 3]
    if offset < 500 or size < 0 or offset + size > len(data):
        raise ValueError(f"table {index} outside metadata bounds")
    if index == 2:
        return offset, size, count
    if count <= 0 or size % count:
        raise ValueError(f"invalid IL2CPP table {index}: offset={offset} size={size} count={count}")
    return offset, size // count, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    metadata = args.metadata.resolve()
    binary = args.binary.resolve()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)

    data = metadata.read_bytes()
    if len(data) < 500 or struct.unpack_from('<II', data) != (0xfab11baf, 108):
        raise ValueError('expected explicit MiniDayZ metadata layout 108')
    string_offset, string_size, _ = table_layout(data, 2)

    def string_at(index: int) -> str | None:
        if not 0 <= index < string_size:
            return None
        start = string_offset + index
        end = data.find(b"\0", start, string_offset + string_size)
        if end < 0:
            return None
        try:
            return data[start:end].decode("utf-8")
        except UnicodeDecodeError:
            return data[start:end].decode("latin1")

    type_offset, type_size, type_count = table_layout(data, 19)
    method_offset, method_size, method_count = table_layout(data, 5)
    field_offset, field_size, field_count = table_layout(data, 11)
    param_offset, param_size, param_count = table_layout(data, 10)
    image_offset, image_size, image_count = table_layout(data, 21)

    types = []
    for index in range(type_count):
        base = type_offset + index * type_size
        types.append(
            {
                "index": index,
                "name": string_at(struct.unpack_from("<i", data, base)[0]),
                "namespace": string_at(struct.unpack_from("<i", data, base + 4)[0]),
                "method_count": struct.unpack_from("<H", data, base + 37)[0],
                "field_count": struct.unpack_from("<H", data, base + 41)[0],
            }
        )

    methods = []
    for index in range(method_count):
        base = method_offset + index * method_size
        methods.append(
            {
                "index": index,
                "name": string_at(struct.unpack_from("<i", data, base)[0]),
                "param_count": struct.unpack_from("<H", data, base + 28)[0],
                "declaring_type_index": struct.unpack_from("<H", data, base + 4)[0],
            }
        )
    param_cursor = 0
    for method in methods:
        method["param_start"] = param_cursor
        param_cursor += method["param_count"]
    if param_cursor != param_count:
        raise RuntimeError(f"parameter ranges mismatch: {param_cursor} != {param_count}")

    # v108 stores method declarations grouped by declaring type, but type records
    # themselves are ordered by type index. Derive each group's start from the
    # declaringType field instead of treating the type table as contiguous.
    method_runs = []
    for index, method in enumerate(methods):
        type_index = method["declaring_type_index"]
        if method_runs and method_runs[-1][0] == type_index:
            method_runs[-1][2] += 1
        else:
            method_runs.append([type_index, index, 1])
    for type_index, start, count in method_runs:
        type_info = types[type_index]
        type_info["method_start"] = start
        if type_info["method_count"] != count:
            raise RuntimeError(
                f"method count mismatch for type {type_index}: {type_info['method_count']} != {count}"
            )

    # Read the actual type fieldStart. Method-bearing type order omits field-only types.
    for type_info in types:
        row = type_offset + type_info['index'] * type_size
        field_start = struct.unpack_from('<H', data, row + 20)[0]
        if type_info['field_count'] and field_start + type_info['field_count'] > field_count:
            raise ValueError('field range outside metadata table')
        type_info['field_start'] = field_start

    fields = [
        string_at(struct.unpack_from("<i", data, field_offset + index * field_size)[0])
        for index in range(field_count)
    ]
    parameters = [
        string_at(struct.unpack_from("<i", data, param_offset + index * param_size)[0])
        for index in range(param_count)
    ]

    images = []
    for index in range(image_count):
        base = image_offset + index * image_size
        images.append(
            {
                "index": index,
                "name": string_at(struct.unpack_from("<i", data, base)[0]),
                "type_start": struct.unpack_from("<H", data, base + 8)[0],
                "type_count": struct.unpack_from("<H", data, base + 10)[0],
            }
        )

    elf = ELFFile(binary.open("rb"))
    sections = {section.name: section for section in elf.iter_sections()}
    il2cpp_section = sections["il2cpp"]
    il2cpp_start = il2cpp_section["sh_addr"]
    il2cpp_end = il2cpp_start + il2cpp_section["sh_size"]
    raw = binary.read_bytes()
    segments = [
        (
            segment["p_vaddr"],
            segment["p_vaddr"] + segment["p_filesz"],
            segment["p_offset"],
            segment["p_offset"] + segment["p_filesz"],
        )
        for segment in elf.iter_segments()
        if segment["p_type"] == "PT_LOAD"
    ]

    def virtual_to_file(address: int) -> int | None:
        for start, end, file_start, file_end in segments:
            if start <= address < end:
                return file_start + address - start
        return None

    rela = sections[".rela.dyn"]
    rela_data = rela.data()
    relocations = {}
    for index in range(rela["sh_size"] // 24):
        offset, info, addend = struct.unpack_from("<QQq", rela_data, index * 24)
        if info & 0xFFFFFFFF == 1027:
            relocations[offset] = addend
    locations_by_target = {}
    for location, target in relocations.items():
        locations_by_target.setdefault(target, []).append(location)

    def string_virtual_address(text: str) -> int | None:
        needle = text.encode() + b"\0"
        location = raw.find(needle)
        while location >= 0:
            for start, end, file_start, file_end in segments:
                if file_start <= location < file_end:
                    return start + location - file_start
            location = raw.find(needle, location + 1)
        return None

    def resolve_module(image: dict):
        expected = sum(
            types[index]["method_count"]
            for index in range(image["type_start"], image["type_start"] + image["type_count"])
        )
        candidates = []
        for name in (image["name"], (image["name"] or "") + "\0"):
            if not name:
                continue
            address = string_virtual_address(name)
            if address is None:
                continue
            for location in locations_by_target.get(address, []):
                file_offset = virtual_to_file(location)
                if file_offset is None:
                    continue
                for field in (0x10, 0x18, 0x8, 0x20):
                    pointer_array = relocations.get(location + field)
                    if pointer_array is None:
                        continue
                    count = struct.unpack_from("<I", raw, file_offset + 8)[0]
                    candidates.append((pointer_array, count))
                    for count_offset in (0x8, 0x10, 0x18, 0xC):
                        alternate = struct.unpack_from("<I", raw, file_offset + count_offset)[0]
                        if alternate:
                            candidates.append((pointer_array, alternate))
        for pointer_array, count in candidates:
            if count == expected and virtual_to_file(pointer_array) is not None:
                return pointer_array, count
        return None

    resolved = 0
    for image in images:
        module = resolve_module(image)
        image["resolved"] = module is not None
        if module:
            image["pointer_array"], image["pointer_count"] = module
            resolved += 1

    rows = []
    for image in images:
        pointer_array = image.get("pointer_array")
        pointer_count = image.get("pointer_count", 0)
        type_end = image["type_start"] + image["type_count"]
        image_methods = [
            method
            for method in methods
            if image["type_start"] <= method["declaring_type_index"] < type_end
        ]
        for pointer_index, method in enumerate(image_methods):
            type_info = types[method["declaring_type_index"]]
            type_name = (
                f"{type_info['namespace']}.{type_info['name']}"
                if type_info["namespace"]
                else type_info["name"]
            )
            address = None
            if pointer_array is not None and pointer_index < pointer_count:
                location = pointer_array + pointer_index * 8
                address = relocations.get(location)
                if address is None:
                    file_offset = virtual_to_file(location)
                    if file_offset is not None:
                        address = struct.unpack_from("<Q", raw, file_offset)[0]
            parameter_names = ",".join(
                parameters[method["param_start"] + offset] or ""
                for offset in range(method["param_count"])
            )
            method["rva"] = address
            method["file_offset"] = virtual_to_file(address) if address else None
            rows.append(
                {
                    "assembly": image["name"],
                    "type": type_name,
                    "method": method["name"] or "",
                    "params": parameter_names,
                    "rva": address,
                    "file_offset": virtual_to_file(address) if address else None,
                }
            )

    with (output / "methods.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["assembly", "type", "method", "params", "rva", "file_offset"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "rva": f"0x{row['rva']:x}" if row["rva"] else "",
                    "file_offset": f"0x{row['file_offset']:x}" if row["file_offset"] is not None else "",
                }
            )

    methods_per_type = {}
    for method in methods:
        methods_per_type.setdefault(method['declaring_type_index'], []).append(method)
    for type_info in types:
        field_start = type_info.get("field_start")
        type_info["fields"] = (
            [
                fields[index]
                for index in range(field_start, field_start + type_info["field_count"])
            ]
            if field_start is not None
            else []
        )
        type_info["methods"] = methods_per_type.get(type_info['index'], [])

    report = {
        "metadata": str(metadata),
        "metadata_sha256": hashlib.sha256(data).hexdigest(),
        "binary": str(binary),
        "binary_sha256": hashlib.sha256(raw).hexdigest(),
        "types": type_count,
        "methods": method_count,
        "images": image_count,
        "resolved_images": resolved,
        "method_rows": len(rows),
        "unresolved_images": [image["name"] for image in images if not image["resolved"]],
    }
    (output / "types.json").write_text(json.dumps(types, ensure_ascii=False), encoding="utf-8")
    (output / "dump_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "methods_by_rva.json").write_text(
        json.dumps(
            {
                f"0x{row['rva']:x}": f"{row['type']}.{row['method']}({row['params']})"
                for row in rows
                if row["rva"]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
