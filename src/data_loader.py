import os
import json
from collections import defaultdict
from src.data_models import Room, Professor


def assign_room_to_pools(room_obj, rules_config):
    assigned_pool = []

    for pool_name, rules in rules_config.items():
        is_match = True

        for column, allowed_values in rules.items():
            if column == "Room_Type":
                actual_val = str(room_obj.r_type).upper()
            elif column == "Building_Block":
                actual_val = str(room_obj.building_block).upper()
            elif column == "Floor":
                actual_val = room_obj.floor
            else:
                actual_val = None

            if isinstance(actual_val, str):
                safe_allowed = [str(v).upper() for v in allowed_values]
                if actual_val not in safe_allowed:
                    is_match = False
                    break

            elif isinstance(actual_val, int):
                safe_allowed = [int(v) for v in allowed_values]
                if actual_val not in safe_allowed:
                    is_match = False
                    break

        if is_match:
            assigned_pool.append(pool_name)

    return assigned_pool


def load_university_data(timeslots_data, classes_data, professors_data, rooms_data) -> dict:
    BASE_DIR = os.path.dirname(__file__)
    # rules_config_path = os.path.join(BASE_DIR, "/rules_config.json")
    rules_config_path = "./rules_config.json"
    pool_rules = {}

    if os.path.exists(rules_config_path):
        with open(rules_config_path, "r") as f:
            config = json.load(f)
            pool_rules = config.get("Room_Pools", {})
    else:
        return {"error": "Room Pools can not be created as the config file does not exist!"}

    # Create a list of all timeslots in the format of "Day_Slot" from the dataframe of timeslots
    all_timeslots = []

    for day, slots in timeslots_data.iterrows():
        slots = slots.dropna().to_dict()
        for slot in slots.values():
            all_timeslots.append(f"{day}_{slot}")

    list_of_room_objects = []
    room_pools = defaultdict(list)
    room_lookup = {}

    for _, row in rooms_data.iterrows():
        room_obj = Room(
            room_id=row["Room_ID"],
            r_type=row["Room_Type"],
            building_block=row["Building_Block"],
            floor=int(row["Floor"])
        )
        list_of_room_objects.append(room_obj)
        room_lookup[room_obj.room_id] = room_obj

        pools_for_this_room = assign_room_to_pools(room_obj, pool_rules)
        for pool in pools_for_this_room:
            room_pools[pool].append(room_obj.room_id)

    list_of_professors = []
    for _, row in professors_data.iterrows():
        prof_obj = Professor(
            prof_id=str(row["Prof_ID"]),
            prof_name=str(row["Professor_Name"]),
            qualified_courses=[c.strip()
                               for c in str(row["Course_ID"]).split(",")],
            max_daily_workload=int(row["Daily_Max_Load"]),
            min_daily_workload=int(row["Daily_Min_Load"]),
            preferred_online_days=[
                d.strip() for d in row["Preferred_Online_Days"].split(",")],
            unavailable_slots=[s.strip()
                               for s in row["Unavailable_Slots"].split(",")],
            disliked_slots=[s.strip()
                            for s in row["Disliked_Slots"].split(",")],
            weekly_max_load=int(row["Weekly_Max_Load"]),
            weekly_min_load=int(row["Weekly_Min_Load"])

        )
        list_of_professors.append(prof_obj)

    # Professor lookup for quick check
    prof_lookup = {p.prof_id: p for p in list_of_professors}

    # Professor pools based on their course expertise
    professor_pools = defaultdict(list)
    for professor in list_of_professors:
        for course in professor.qualified_courses:
            professor_pools[course].append(professor.prof_id)

    # Creating genes that is templates for each slot of timetable
    genes_list = []
    for _, row in classes_data.iterrows():
        for i in range(row["Weekly_Count"]):
            genes_list.append({
                "course_id": row["Course_ID"],
                "section_id": row["Section"],
                "semester": row["Semester"],
                "r_type": row["Type"],
                "duration": int(row["Duration"]),
                "delivery_mode": row["Delivery_Mode"],
                "session_number": i + 1,
                "assigned_prof": None,
                "assigned_slot": None,
                "assigned_room": None
            })

    return {
        "room_pools": room_pools,
        "room_lookup": room_lookup,
        "professor_pools": professor_pools,
        "professor_lookup": prof_lookup,
        "genes_list": genes_list,
        "timeslots": all_timeslots
    }
