import json
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="JSON Cell Parser",
    page_icon="🧾",
    layout="wide"
)

st.title("🧾 JSON Cell Parser")
st.write("Paste JSON from a data table cell below.")


def count_nested_items(value):
    """
    Counts nested JSON containers:
    - dict objects
    - list arrays
    """
    if isinstance(value, dict):
        return 1 + sum(count_nested_items(v) for v in value.values())

    if isinstance(value, list):
        return 1 + sum(count_nested_items(item) for item in value)

    return 0


def build_element_summary(data):
    rows = []

    if isinstance(data, dict):
        for key, value in data.items():
            rows.append({
                "element": key,
                "type": type(value).__name__,
                "nested_objects_or_arrays": count_nested_items(value),
            })

    elif isinstance(data, list):
        for index, value in enumerate(data):
            rows.append({
                "element": f"[{index}]",
                "type": type(value).__name__,
                "nested_objects_or_arrays": count_nested_items(value),
            })

    else:
        rows.append({
            "element": "root",
            "type": type(data).__name__,
            "nested_objects_or_arrays": count_nested_items(data),
        })

    return pd.DataFrame(rows)


def value_preview(value, max_length=120):
    """Make values readable in the search result table."""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)

    if len(text) > max_length:
        return text[:max_length] + "..."

    return text


def find_json_matches(data, search_term, path="$"):
    """
    Recursively search JSON for matching keys, paths, or values.

    Returns rows with:
    - path
    - match_type
    - key
    - value_preview
    """
    matches = []

    if not search_term:
        return matches

    search_lower = search_term.lower()

    if isinstance(data, dict):
        for key, value in data.items():
            key_text = str(key)
            current_path = f"{path}.{key_text}"

            key_matches = search_lower in key_text.lower()
            path_matches = search_lower in current_path.lower()

            if key_matches or path_matches:
                matches.append({
                    "path": current_path,
                    "match_type": "key/path",
                    "key": key_text,
                    "value_preview": value_preview(value),
                })

            matches.extend(find_json_matches(value, search_term, current_path))

    elif isinstance(data, list):
        for index, item in enumerate(data):
            current_path = f"{path}[{index}]"

            path_matches = search_lower in current_path.lower()

            if path_matches:
                matches.append({
                    "path": current_path,
                    "match_type": "path",
                    "key": f"[{index}]",
                    "value_preview": value_preview(item),
                })

            matches.extend(find_json_matches(item, search_term, current_path))

    else:
        value_text = str(data)
        value_matches = search_lower in value_text.lower()

        if value_matches:
            matches.append({
                "path": path,
                "match_type": "value",
                "key": "",
                "value_preview": value_preview(data),
            })

    return matches


raw_text = st.text_area(
    "Paste cell contents here",
    height=300,
    placeholder='Example: {"device": {"rssi": -72, "status": "online"}}'
)

expanded = st.checkbox("Expand JSON structure by default", value=True)

search_term = st.text_input(
    "Search keys, paths, or values",
    placeholder="Example: rssi"
)

if raw_text.strip():
    try:
        parsed_json = json.loads(raw_text)

        st.success("Valid JSON")

        total_nested_count = count_nested_items(parsed_json)

        st.metric(
            label="Total nested objects/arrays",
            value=total_nested_count
        )

        if search_term.strip():
            st.subheader(f"Search results for `{search_term}`")

            matches = find_json_matches(parsed_json, search_term.strip())
            matches_df = pd.DataFrame(matches)

            if matches_df.empty:
                st.warning("No matching paths found.")
            else:
                st.write(f"Found `{len(matches_df)}` matching path(s).")
                st.dataframe(matches_df, use_container_width=True)

                with st.expander("Copy matching paths"):
                    paths_text = "\n".join(matches_df["path"].tolist())
                    st.code(paths_text, language="text")

        st.subheader("Summary by top-level element")
        summary_df = build_element_summary(parsed_json)
        st.dataframe(summary_df, use_container_width=True)

        st.subheader("Pretty JSON structure")
        st.json(parsed_json, expanded=expanded)

        st.subheader("Pretty formatted JSON text")
        st.code(
            json.dumps(parsed_json, indent=2, ensure_ascii=False),
            language="json"
        )

    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e.msg}")
        st.write(f"Line: `{e.lineno}`")
        st.write(f"Column: `{e.colno}`")

else:
    st.info("Paste JSON above to parse it.")