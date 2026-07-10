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


raw_text = st.text_area(
    "Paste cell contents here",
    height=300,
    placeholder='Example: {"name": "Toby", "age": 5, "traits": ["cute", "chaotic"]}'
)

expanded = st.checkbox("Expand JSON structure by default", value=True)

if raw_text.strip():
    try:
        parsed_json = json.loads(raw_text)

        st.success("Valid JSON")

        total_nested_count = count_nested_items(parsed_json)

        st.metric(
            label="Total nested objects/arrays",
            value=total_nested_count
        )

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