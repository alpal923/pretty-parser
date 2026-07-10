import json
import streamlit as st
import pandas as pd
from collections import defaultdict

st.set_page_config(
    page_title="JSON Structure Parser",
    page_icon="🧾",
    layout="wide"
)

st.title("🧾 JSON Structure Parser")
st.write("Paste one JSON object, a JSON array, or multiple JSON objects from data table cells.")


def parse_multiple_json_packages(raw_text):
    """
    Supports:
    1. One JSON object
    2. A JSON array of objects
    3. Newline-delimited JSON objects
    """
    raw_text = raw_text.strip()

    if not raw_text:
        return []

    # First, try parsing the entire input as valid JSON.
    try:
        parsed = json.loads(raw_text)

        if isinstance(parsed, list):
            return parsed

        return [parsed]

    except json.JSONDecodeError:
        pass

    # If that fails, try parsing line-by-line.
    packages = []
    errors = []

    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()

        if not line:
            continue

        try:
            packages.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append(
                f"Line {line_number}: {e.msg} at column {e.colno}"
            )

    if errors:
        raise ValueError("\n".join(errors))

    return packages


def type_name(value):
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"

    return type(value).__name__


def value_preview(value, max_length=120):
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)

    if len(text) > max_length:
        return text[:max_length] + "..."

    return text


def walk_json_structure(value, path="$", rows=None):
    """
    Walk every path in a JSON package.
    Arrays use [] as a generic placeholder so similar structures line up:
    $.events[].rssi instead of $.events[0].rssi
    """
    if rows is None:
        rows = []

    rows.append({
        "path": path,
        "type": type_name(value),
        "example_value": value_preview(value)
    })

    if isinstance(value, dict):
        for key, child_value in value.items():
            child_path = f"{path}.{key}"
            walk_json_structure(child_value, child_path, rows)

    elif isinstance(value, list):
        for item in value:
            child_path = f"{path}[]"
            walk_json_structure(item, child_path, rows)

    return rows


def build_common_structure(packages):
    """
    Builds a dataframe showing:
    - every shared/possible path
    - how many JSON packages contain that path
    - percentage coverage
    - observed types
    - example value
    """
    path_info = defaultdict(lambda: {
        "package_indexes": set(),
        "types": set(),
        "examples": []
    })

    for package_index, package in enumerate(packages):
        rows = walk_json_structure(package)

        # Deduplicate paths within a single package so arrays do not overcount.
        paths_seen_in_package = set()

        for row in rows:
            path = row["path"]

            path_info[path]["types"].add(row["type"])

            if len(path_info[path]["examples"]) < 3:
                path_info[path]["examples"].append(row["example_value"])

            if path not in paths_seen_in_package:
                path_info[path]["package_indexes"].add(package_index)
                paths_seen_in_package.add(path)

    summary_rows = []

    total_packages = len(packages)

    for path, info in path_info.items():
        package_count = len(info["package_indexes"])
        coverage_percent = round((package_count / total_packages) * 100, 1)

        summary_rows.append({
            "path": path,
            "packages_with_path": package_count,
            "total_packages": total_packages,
            "coverage_percent": coverage_percent,
            "common_to_all": package_count == total_packages,
            "observed_types": ", ".join(sorted(info["types"])),
            "example_value": info["examples"][0] if info["examples"] else ""
        })

    df = pd.DataFrame(summary_rows)

    return df.sort_values(
        by=["common_to_all", "coverage_percent", "path"],
        ascending=[False, False, True]
    )


def find_json_matches_in_packages(packages, search_term):
    matches = []
    search_lower = search_term.lower()

    for package_index, package in enumerate(packages):
        rows = walk_json_structure(package)

        for row in rows:
            path = row["path"]
            example_value = row["example_value"]

            if (
                search_lower in path.lower()
                or search_lower in str(example_value).lower()
            ):
                matches.append({
                    "package_number": package_index + 1,
                    "path": path,
                    "type": row["type"],
                    "example_value": example_value
                })

    return pd.DataFrame(matches)


raw_text = st.text_area(
    "Paste JSON package(s) here",
    height=350,
    placeholder="""Examples:

{"device": {"rssi": -72, "status": "online"}}
{"device": {"rssi": -68, "status": "offline"}}

OR

[
  {"device": {"rssi": -72, "status": "online"}},
  {"device": {"rssi": -68, "status": "offline"}}
]
"""
)

expanded = st.checkbox("Expand JSON packages by default", value=False)

search_term = st.text_input(
    "Search paths or values",
    placeholder="Example: rssi"
)

only_common = st.checkbox("Show only paths common to all packages", value=False)

if raw_text.strip():
    try:
        packages = parse_multiple_json_packages(raw_text)

        st.success(f"Parsed {len(packages)} JSON package(s).")

        common_structure_df = build_common_structure(packages)

        if only_common:
            display_structure_df = common_structure_df[
                common_structure_df["common_to_all"] == True
            ]
        else:
            display_structure_df = common_structure_df

        st.subheader("Common structure")
        st.dataframe(display_structure_df, use_container_width=True)

        with st.expander("Copy common paths"):
            common_paths = common_structure_df[
                common_structure_df["common_to_all"] == True
            ]["path"].tolist()

            st.code("\n".join(common_paths), language="text")

        if search_term.strip():
            st.subheader(f"Search results for `{search_term}`")

            search_df = find_json_matches_in_packages(
                packages,
                search_term.strip()
            )

            if search_df.empty:
                st.warning("No matching paths or values found.")
            else:
                st.write(f"Found {len(search_df)} match(es).")
                st.dataframe(search_df, use_container_width=True)

                with st.expander("Copy matching paths"):
                    st.code(
                        "\n".join(search_df["path"].drop_duplicates().tolist()),
                        language="text"
                    )

        st.subheader("Pretty JSON packages")

        for index, package in enumerate(packages, start=1):
            with st.expander(f"Package {index}", expanded=expanded):
                st.json(package, expanded=expanded)

        st.subheader("Pretty formatted JSON text")

        for index, package in enumerate(packages, start=1):
            with st.expander(f"Formatted package {index}", expanded=False):
                st.code(
                    json.dumps(package, indent=2, ensure_ascii=False),
                    language="json"
                )

    except ValueError as e:
        st.error("Could not parse multiple JSON packages.")
        st.code(str(e), language="text")

    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e.msg}")
        st.write(f"Line: `{e.lineno}`")
        st.write(f"Column: `{e.colno}`")

else:
    st.info("Paste one or more JSON packages above to parse them.")