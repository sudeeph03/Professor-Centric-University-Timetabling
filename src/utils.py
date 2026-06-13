import random


def get_pool_key(gene):
    """
    This function is used to get pool key which will be used to assign the right room to the right section based on the type of class, semester and preferred mode.
    """
    course_type = gene["r_type"].upper()
    semester = gene["semester"].upper()
    student_group = gene["section_id"].upper()

    if course_type == 'LAB':
        return 'LABS'

    if course_type in ("STUDIO", "ONLINE"):
        return 'STUDIOS'

    if course_type == "LECTURE":
        semester_num = semester.replace("SEM", "")
        department = student_group.split(
            "_")[0] if "_" in student_group else ""

        return f"{department}_SEM{semester_num}_THEORY"

    return None


def get_valid_starting_slot(duration: int, all_timeslots: list):
    """
    This function returns a valid slot based on the duration so the class does not spill to the next day
    """
    if duration <= 1:
        return random.choice(all_timeslots)

    while True:
        start_index = random.randint(0, len(all_timeslots) - 1)
        start_slot = all_timeslots[start_index]
        start_day = start_slot.split("_")[0]

        if "lunch" in start_slot.lower() or "break" in start_slot.lower():
            continue

        is_valid = True
        for i in range(1, duration):
            next_index = start_index + i

            if next_index >= len(all_timeslots):
                is_valid = False
                break

            check_slot = all_timeslots[next_index]
            if check_slot.split("_")[0] != start_day:
                is_valid = False
                break

            if "lunch" in check_slot.lower() or "break" in check_slot.lower():
                is_valid = False
                break

        if is_valid:
            return start_slot


def get_occupied_slots(start_slot: str, duration: int, slots_to_order_map: dict, order_to_slots_map: dict):
    start_order = slots_to_order_map[start_slot]
    return [order_to_slots_map[start_order + i] for i in range(int(duration))]
