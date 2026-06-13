import streamlit as st
import json
import os

CONFIG_FILE = 'rules_config.json'


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"Room_Pools": {}}


def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)


st.set_page_config(page_title="Rule Configuration", page_icon="⚙️")
st.title("⚙️ University Layout Rules")

config = load_config()

# For basic update or addtion of rooms in existing room pools
st.subheader("📝 Add or Update a Single Rule")
st.markdown(
    "Use this option to update existing room pools or add a room to a room pool")

with st.form("rule_builder_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        pool_name = st.text_input("Pool Name to Add/Edit").strip().upper()
        room_types = st.multiselect("Allowed Room Types", [
                                    "LECTURE", "LAB", "ONLINE", "STUDIO"])
    with col2:
        building_blocks = st.text_input("Building Blocks (comma separated)")
        floors = st.text_input("Floors (comma separated)")

    if st.form_submit_button("Save Rule"):
        if pool_name:
            new_rule = {}
            if room_types:
                new_rule["Room_Type"] = room_types

            blocks_list = [b.strip().upper()
                           for b in building_blocks.split(",") if b.strip()]
            if blocks_list:
                new_rule["Building_Block"] = blocks_list

            floors_list = [int(f.strip())
                           for f in floors.split(",") if f.strip().isdigit()]
            if floors_list:
                new_rule["Floor"] = floors_list

            # Updates just this one specific rule and saves the whole file
            config["Room_Pools"][pool_name] = new_rule
            save_config(config)
            st.success(f"Updated {pool_name}!")
            st.rerun()

st.divider()

# Overwrite existing rules with brand new rules for room pools
st.subheader("📁 Overwrite Exiting Rules for a new Layout")
st.markdown(
    "Have a massive update? Upload a full JSON file to instantly overwrite all rules.")

uploaded_file = st.file_uploader("Choose a JSON file", type=["json"])
if uploaded_file is not None:
    try:
        new_rules = json.load(uploaded_file)
        if "Room_Pools" in new_rules:
            save_config(new_rules)
            st.success("Rules file updated successfully!")
            st.rerun()
        else:
            st.error("Invalid file format!")
    except Exception as e:
        st.error(f"Upload failed: {e}")

st.divider()

# Exising rules
st.subheader("Current Active Engine Rules")
st.json(config.get("Room_Pools", {}), expanded=False)
