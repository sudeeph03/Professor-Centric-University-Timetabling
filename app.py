import streamlit as st
import pandas as pd
import io
from src.main import ga_for_dual_delivery
import logging

logging.getLogger(
    "streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)

st.set_page_config(page_title="Timetable Generator",
                   layout="wide", initial_sidebar_state="expanded")

st.title("University Timetable Generator for Dual Delivery")
st.markdown("-----")

st.header("Upload your data files here: ")
col1, col2, col3, col4 = st.columns(4)

with col1:
    timeslots_file = st.file_uploader("Timeslots file (CSV): ", type=["csv"])
with col2:
    classes_file = st.file_uploader("Classes file (CSV): ", type=["csv"])
with col3:
    professors_file = st.file_uploader("Professors file (CSV): ", type=["csv"])
with col4:
    rooms_file = st.file_uploader("Rooms file (CSV): ", type=["csv"])


st.header("Generate Timetable: ")
start_generation_btn = st.button(
    "Start Generation", type="primary", use_container_width=True)

if start_generation_btn:
    if timeslots_file and classes_file and professors_file and rooms_file:
        with st.spinner("Your timetable is being generated... Please Wait"):
            try:
                slots_df = pd.read_csv(timeslots_file, index_col=0)
                classes_df = pd.read_csv(classes_file)
                professors_df = pd.read_csv(professors_file)
                professors_df.fillna("", inplace=True)
                rooms_df = pd.read_csv(rooms_file)

                status_text = st.empty()

                optimal_schedule = ga_for_dual_delivery(
                    slots_df, classes_df, professors_df, rooms_df, status_text)

                st.session_state["optimal_schedule"] = optimal_schedule
                st.session_state["timeslots"] = slots_df
                status_text.empty()
                st.success(
                    "Timetables generated successfully! Scroll down to view them.")
            except Exception as e:
                st.error(
                    f"An error occured during the generation cycle: {str(e)}")
    else:
        st.warning(
            ("Please upload all required files before you hit start generation!"))


def display_timetable(schedule_data, days, slots, view_name, selected_value):
    table = pd.DataFrame(index=slots, columns=days)
    table.fillna("-", inplace=True)

    if "Lunch" in table.index:
        table.loc["Lunch"] = "BREAK"

    for session in schedule_data:
        timeslot = session["assigned_slot"]
        duration = session.get("duration", 1)

        if "_" in timeslot:
            day, slot = timeslot.split("_")
            course = session["course_id"]
            section = session["section_id"]
            room = session["assigned_room"]

            if slot in slots:
                start_index = slots.index(slot)

                for i in range(duration):
                    if start_index+i < len(slots):
                        current_slot = slots[start_index+i]

                    if current_slot.lower() == "lunch" or current_slot.lower() == "break":
                        continue

                    cell_content = ""
                    if view_name == "Professor":
                        cell_content = f"{section} | {room} | {course}"
                    else:
                        cell_content = f"{course} | {room}"

                    if duration > 1:
                        cell_content += f" Hr {i+1}/{duration}"
                    if day in table.columns:
                        current_cell = str(table.at[current_slot, day])
                        if current_cell == "-" or current_cell == "BREAK":
                            table.at[current_slot, day] = cell_content
                        else:
                            table.at[current_slot, day] = current_cell + \
                                f"\n----\n {cell_content}"

    st.dataframe(table, use_container_width=True)

    # Download buttons to save the generated timetable for a professor or section locally
    st.markdown("Download Schedule:")
    d_col1, d_col2 = st.columns(2)

    csv_df = table.copy()
    for col in csv_df.columns:
        csv_df[col] = csv_df[col].apply(lambda x: str(x).replace("\n", "|"))
    csv_file = csv_df.reset_index().rename(columns={"index": "Time Slot"})

    with d_col1:
        st.download_button(
            label="📥 Download Timetable as CSV",
            data=csv_file.to_csv(index=False).encode('utf-8'),
            file_name=f"{view_name}_{selected_value}_schedule.csv",
            mime="text/csv",
            key=f"dl {view_name}_{selected_value}",
            use_container_width=True
        )

    # XLSX file download
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        table.to_excel(
            writer, sheet_name="Schedule", index=True)
    excel_data = buffer.getvalue()

    with d_col2:
        st.download_button(
            label="📥 Download Timetable as XLSX (Recommended)",
            data=excel_data,
            file_name=f"{selected_value}_schedule.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


if "optimal_schedule" in st.session_state:
    st.header("Faculty Schedules: ")

    tab1, tab2 = st.tabs(["Professor View", "Section View"])

    schedule_data = st.session_state["optimal_schedule"]
    timeslot_df = st.session_state["timeslots"]
    days = timeslot_df.index.tolist()
    slots = timeslot_df.iloc[0].tolist()

    with tab1:
        unique_profs = sorted(list(set(
            [entry["assigned_prof"] for entry in schedule_data if entry.get("assigned_prof")])))

        selected_prof = st.selectbox(
            "Professors: ", unique_profs, key="prof_select")

        if selected_prof:
            prof_data = [
                row for row in schedule_data if row["assigned_prof"] == selected_prof]
            display_timetable(prof_data, days, slots,
                              "Professor", selected_prof)

    with tab2:
        unique_sections = sorted(list(
            set([entry["section_id"] for entry in schedule_data if entry.get("section_id")])))
        selected_section = st.selectbox(
            "Sections: ", unique_sections, key="sec_select")

        if selected_section:
            section_data = [row for row in schedule_data if row.get(
                'section_id') == selected_section]
            display_timetable(section_data, days, slots,
                              "Section", selected_section)
