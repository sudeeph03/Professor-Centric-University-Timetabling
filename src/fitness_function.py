from collections import defaultdict
from typing import List, Dict, Union, Any, Tuple
from src.utils import get_pool_key, get_occupied_slots


HARD_PENALTY = 1000
SOFT_PENALTY = 40
WORKLOAD_PENALTY = 80
OVERLOAD_PENALTY = 800
UNDERLOAD_PENALTY = 100
MODALITY_JUMP_PENALTY = 50
TRAVEL_PENALTY = 50
LUNCH_PENALTY = 1000


def fitness_function(timetable, all_timeslots, room_pools, room_lookup, prof_lookup, slots_to_day_map, slots_to_order_map, order_to_slots_map) -> Union[float, Tuple[float, Dict[str, Any]]]:
    """
    This is the main function in fitness evaluation that adds the penalties from each constraint tracking functions
    """
    fitness = 0
    penalty = 0

    clash_penalty = _check_clash_violations(
        timetable, slots_to_order_map, order_to_slots_map)
    professor_unavailability_penalty = _check_professor_unavailability(
        timetable, prof_lookup, slots_to_order_map, order_to_slots_map)
    workload_penalty = _check_professor_workload(
        timetable, all_timeslots, slots_to_day_map, prof_lookup)
    room_penalty = _check_room_and_modality_violations(timetable, room_pools)
    professor_transition_penalty = _check_professor_transitions(
        timetable, room_lookup, slots_to_day_map, slots_to_order_map)
    prof_online_pref_pen = _check_professor_online_preference(
        timetable, prof_lookup)
    student_penalty = _check_student_gap_violations(
        timetable, slots_to_day_map, slots_to_order_map)
    consecutive_penalty = _check_consecutive_lectures(
        timetable, slots_to_day_map, slots_to_order_map)
    lunch_pen = _check_lunch_violations(
        timetable, slots_to_order_map, order_to_slots_map)

    penalty = clash_penalty + professor_unavailability_penalty + \
        workload_penalty + room_penalty + \
        professor_transition_penalty + prof_online_pref_pen + \
        student_penalty + consecutive_penalty + lunch_pen

    max_fitness = (len(timetable) * HARD_PENALTY)
    fitness = max_fitness - penalty
    raw_fitness = max(0, fitness)
    real_fitness = raw_fitness / max_fitness

    return real_fitness


def _check_clash_violations(timetable: List[Dict], slots_to_order_map: dict, order_to_slots_map: dict) -> int:
    """
    This function checks for clashes like overlapping professor, student group and double booking a room
    """
    penalty = 0

    timeslot_professor = set()
    timeslot_rooms = set()
    timeslot_sections = set()

    for single_class in timetable:
        timeslot = single_class["assigned_slot"]
        professor = single_class["assigned_prof"]
        room = single_class["assigned_room"]
        section = single_class["section_id"]
        duration = int(single_class.get("duration", 1))

        occupied_slots = get_occupied_slots(
            timeslot, duration, slots_to_order_map, order_to_slots_map)

        for slot in occupied_slots:
            # Check professor clashes
            prof_key = (slot, professor)
            if prof_key in timeslot_professor:
                penalty += HARD_PENALTY
            else:
                timeslot_professor.add(prof_key)

            # Check room clashes
            room_key = (slot, room)
            if room_key in timeslot_rooms:
                penalty += HARD_PENALTY
            else:
                timeslot_rooms.add(room_key)

            # Check section clashes
            section_key = (slot, section)
            if section_key in timeslot_sections:
                penalty += HARD_PENALTY
            else:
                timeslot_sections.add(section_key)

    return penalty


def _check_professor_unavailability(timetable: List[Dict], prof_lookup: Dict, slot_to_order_map: dict, order_to_slot_map: dict) -> int:
    """
    This function checks where the class has been assigned to either their unavailable timeslots or their dislikes timeslots  
    """
    penalty = 0

    for single_class in timetable:
        timeslot = single_class["assigned_slot"]
        professor = single_class["assigned_prof"]
        duration = single_class["duration"]

        prof_obj = prof_lookup.get(professor)

        if not prof_obj:
            continue

        occupied_slots = get_occupied_slots(
            timeslot, duration, slot_to_order_map, order_to_slot_map)

        for slot in occupied_slots:
            if slot in prof_obj.unavailable_slots:
                penalty += HARD_PENALTY
            elif slot in prof_obj.disliked_slots:
                penalty += SOFT_PENALTY

    return penalty


def _check_professor_workload(timetable: List[Dict], all_timeslots: list, slot_to_day_map: Dict, prof_lookup: Dict) -> list:
    """
    This function checks the daily and weekly workload so that the workload of the professors follows the daily and weekly limits set by the university 
    """
    penalty = 0

    working_days = set(slot_to_day_map.values())
    professor_daily_counts = defaultdict(int)
    professor_weekly_counts = {prof_id: 0 for prof_id in prof_lookup}

    for single_class in timetable:
        timeslot = single_class["assigned_slot"]
        professor = single_class["assigned_prof"]
        duration = single_class["duration"]

        if not professor or professor not in prof_lookup:
            continue

        day = slot_to_day_map[timeslot]
        professor_daily_counts[(professor, day)] += duration
        professor_weekly_counts[professor] += duration

    for prof_id, prof_details in prof_lookup.items():
        max_classes_per_day = prof_details.max_daily_workload
        min_classes_per_day = prof_details.min_daily_workload

        for day in working_days:
            count = professor_daily_counts.get((prof_id, day), 0)

            if count > max_classes_per_day:
                extra_classes = count - max_classes_per_day
                penalty += extra_classes * WORKLOAD_PENALTY
            elif count > 0 and count < min_classes_per_day:
                missing_classes = min_classes_per_day - count
                penalty += missing_classes * WORKLOAD_PENALTY
                
    for prof, count in professor_weekly_counts.items():
        prof_obj = prof_lookup[prof]
        MIN_WEEKLY_CLASSES = prof_obj.weekly_min_load
        MAX_WEEKLY_CLASSES = prof_obj.weekly_max_load

        if count < MIN_WEEKLY_CLASSES:
            missing_classes = MIN_WEEKLY_CLASSES - count
            penalty += missing_classes * UNDERLOAD_PENALTY
        elif count > MAX_WEEKLY_CLASSES:
            extra_classes = count - MAX_WEEKLY_CLASSES
            penalty += extra_classes * OVERLOAD_PENALTY

    return penalty


def _check_professor_online_preference(timetable: List[Dict], prof_lookup: Dict) -> int:
    """
    This function helps in assigning online classes to professor preferred day to conduct the class
    """
    penalty = 0
    for single_class in timetable:
        professor = single_class["assigned_prof"]
        timeslot = single_class["assigned_slot"]
        delivery_mode = single_class["delivery_mode"]
        day = timeslot.split("_")[0]

        if not professor or not timeslot:
            continue

        prof_obj = prof_lookup[professor]

        if delivery_mode.upper() == "ONLINE" and prof_obj:
            preferred_days = prof_obj.preferred_online_days
            if len(preferred_days) > 0:
                if day not in preferred_days:
                    penalty += SOFT_PENALTY

    return penalty


def _check_room_and_modality_violations(timetable: List[Dict], room_pools: Dict) -> int:
    """
    This function checks whether a room pool exist and a room exists in the required room pool
    """
    penalty = 0

    for single_class in timetable:
        room = single_class["assigned_room"]

        required_pool_key = get_pool_key(single_class)

        if required_pool_key:

            if required_pool_key not in room_pools:
                penalty += HARD_PENALTY

            if room not in room_pools[required_pool_key]:
                penalty += HARD_PENALTY

    return penalty


def _check_professor_transitions(timetable: List[Dict], room_lookup: Dict, slots_to_day_map: Dict, slots_to_order_map: Dict) -> int:
    """
    This function checks the transtion times between online and offline classes
    It also checks for travel between buidlings of the campus
    """
    penalty = 0

    prof_schedules = defaultdict(list)

    # Group all slots for each professor by day
    for single_class in timetable:
        professor = single_class["assigned_prof"]
        timeslot = single_class["assigned_slot"]
        room = single_class["assigned_room"]
        duration = single_class["duration"]

        if not professor or not room:
            continue

        day = slots_to_day_map[timeslot]
        order = slots_to_order_map[timeslot]

        prof_schedules[(professor, day)].append((order, duration, room))

    # Check for travel time violations for each professor on each day
    for (professor, day), classes in prof_schedules.items():

        if len(classes) <= 1:
            continue

        classes.sort(key=lambda x: x[0])

        # Check for building switches
        for i in range(len(classes)-1):
            order1, duration1, room1 = classes[i]
            order2, duration2, room2 = classes[i+1]

            expected_next_start = order1+duration1

            if order2 == expected_next_start:
                room1_obj = room_lookup[room1]
                room2_obj = room_lookup[room2]

                if room1_obj and room2_obj:
                    if room1_obj.building_block != room2_obj.building_block:
                        penalty += TRAVEL_PENALTY

                type1_online = (room1_obj.r_type.upper(
                ) == "ONLINE" or room1_obj.r_type.upper() == "STUDIO")
                type2_online = (room2_obj.r_type.upper(
                ) == "ONLINE" or room2_obj.r_type.upper() == "STUDIO")

                if type1_online ^ type2_online:
                    penalty += MODALITY_JUMP_PENALTY

    return penalty


def _check_student_gap_violations(timetable: List[Dict], slots_to_day_map: Dict, slots_to_order_map: Dict) -> int:
    """
    This function ensures that the timetable is deployable and realistic with normal amount of idle student gaps
    """
    penalty = 0

    scheduled_sections = defaultdict(list)

    for single_class in timetable:
        section = single_class["section_id"]
        timeslot = single_class["assigned_slot"]
        duration = single_class["duration"]

        day = slots_to_day_map[timeslot]
        start_order = slots_to_order_map[timeslot]
        end_order = start_order + int(duration)-1

        scheduled_sections[(section, day)].append((start_order, end_order))

    for (section, day), daily_schedule in scheduled_sections.items():
        if len(daily_schedule) <= 1:
            continue

        daily_schedule.sort(key=lambda x: x[0])
        for i in range(len(daily_schedule)-1):
            current_class = daily_schedule[i][1]
            next_class = daily_schedule[i+1][0]

            class_gap = (next_class - current_class) - 1
            if class_gap > 1:
                penalty += (class_gap ** 2) * SOFT_PENALTY

    return penalty


def _check_consecutive_lectures(timetable: List[Dict], slots_to_day_map: Dict, slots_to_order_map: Dict) -> int:
    """
    This function ensures that a course is not being assinged muliple times in a row to avoid professor and student fatigue
    """
    penalty = 0

    section_daily_schedule = defaultdict(list)

    for single_class in timetable:
        section = single_class["section_id"]
        course = single_class["course_id"]
        r_type = single_class["r_type"]
        timeslot = single_class["assigned_slot"]
        duration = single_class["duration"]

        day = slots_to_day_map[timeslot]
        order = slots_to_order_map[timeslot]

        section_daily_schedule[(section, day)].append(
            (course, r_type, order, duration))

    for (section, day), classes in section_daily_schedule.items():
        if len(classes) < 2:
            continue

        classes.sort(key=lambda x: x[2])

        for i in range(len(classes)-1):
            current_course, current_r_type, current_order, current_duration = classes[i]
            next_course, next_r_type, next_order, next_duration = classes[i+1]

            expected_next_start = current_order + current_duration

            if (current_course == next_course) and (next_order == expected_next_start) and (current_r_type == next_r_type):
                penalty += HARD_PENALTY

    return penalty


def _check_lunch_violations(timetable: List[Dict], slot_to_order_map: dict, order_to_slot_map: dict) -> int:
    """
    This function ensures that a class is not assinged to break session
    """
    penalty = 0

    for single_class in timetable:
        start_slot = single_class["assigned_slot"]
        duration = single_class["duration"]

        occupied_slots = get_occupied_slots(
            start_slot, duration, slot_to_order_map, order_to_slot_map)

        for slot in occupied_slots:
            if "lunch" in slot.lower() or "break" in slot.lower():
                penalty += HARD_PENALTY

    return penalty
