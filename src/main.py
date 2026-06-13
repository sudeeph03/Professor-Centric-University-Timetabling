import random
import time
import concurrent.futures
from collections import defaultdict
from functools import partial

from src.data_loader import load_university_data
from src.fitness_function import fitness_function
from src.utils import get_pool_key, get_valid_starting_slot


def initialize_gene(template_gene: dict, all_timeslots: list, room_pool: dict, professor_pool: dict, prof_load_tracker: dict):
    """
    Creates a gene or a class to be assinged by assigning professor, timeslot and room to the gene templates.
    The professor is assinged based on their workload.
    The room is selected from the required room pool.
    The timeslot is selected based on the duraion so that it does not spill into next day.
    """
    # Creaating a copy of the gene template to ensure that the original template is not modified during initialization.
    new_gene = template_gene.copy()

    course_id = new_gene['course_id']
    if course_id in professor_pool and professor_pool[course_id]:
        # Get the list of qualified professors
        qualified_profs = professor_pool[course_id]

        # professor selection based on current workload to distrbute workload evenly
        best_prof = min(qualified_profs, key=lambda p: prof_load_tracker[p])
        new_gene['assigned_prof'] = best_prof
        prof_load_tracker[best_prof] += 1

    # Assign a random room from the appropriate pool based on the semester and type of class
    pool_key = get_pool_key(new_gene)
    if pool_key in room_pool and room_pool[pool_key]:
        new_gene['assigned_room'] = random.choice(room_pool[pool_key])

    # Assign a random timeslot
    new_gene['assigned_slot'] = get_valid_starting_slot(
        new_gene["duration"], all_timeslots)

    return new_gene


def create_chromosome(genes_list: list, all_timeslots: list, room_pools: dict, professor_pools: dict):
    """
    Creates a timetable for initial population using the initialize_gene function
    """

    chromosome = []
    # This tracks the number of classes assigned to each professor and allows to manage distribution of workload of a course
    prof_load_tracker = defaultdict(int)

    for gene_template in genes_list:
        initialized_gene = initialize_gene(
            gene_template, all_timeslots, room_pools, professor_pools, prof_load_tracker)
        chromosome.append(initialized_gene)
    return chromosome


def create_population(population_size: int, genes_list: list, all_timeslots: list, room_pools: dict, professor_pools: dict):
    """
    This function creates intial population of timetables by using the create_chromosome function
    """
    population = []

    for _ in range(population_size):
        timetable = create_chromosome(
            genes_list, all_timeslots, room_pools, professor_pools)
        population.append(timetable)

    return population


def tournament_selection(population: list, tournament_size=6):
    """
    This function picks the best timetable based on fitness score among the timetables present in the tounament size.
    """
    competitors = random.sample(population, tournament_size)

    winner = max(competitors, key=lambda x: x[1])

    return winner[0]


def heuristic_crossover(parent1: list, parent2: list):
    """
    This function effectively picks a good gene from two parents based on the number of conflicts in each gene.
    The gene with no conflicts is se;ected and pushed.
    If either gene has a conflict or both are valid, it randomly select one of them and pushes it to the offspring timetable
    """
    new_child = []

    child_prof_schedule = set()
    child_room_schedule = set()
    child_section_schedule = set()

    for class1, class2 in zip(parent1, parent2):
        prof1 = class1["assigned_prof"]
        room1 = class1["assigned_room"]
        section1 = class1["section_id"]
        slot1 = class1["assigned_slot"]

        prof2 = class2["assigned_prof"]
        room2 = class2["assigned_room"]
        section2 = class2["section_id"]
        slot2 = class2["assigned_slot"]

        p1_conflict = (slot1, prof1) in child_prof_schedule or (
            slot1, room1) in child_room_schedule or (slot1, section1) in child_section_schedule
        p2_conflict = (slot2, prof2) in child_prof_schedule or (
            slot2, room2) in child_room_schedule or (slot2, section2) in child_section_schedule

        if p1_conflict and not p2_conflict:
            chosen = class2
        elif p2_conflict and not p1_conflict:
            chosen = class1
        else:
            chosen = class1 if random.random() < 0.5 else class2

        new_child.append(chosen)

        child_prof_schedule.add(
            (chosen["assigned_slot"], chosen["assigned_prof"]))
        child_room_schedule.add(
            (chosen["assigned_slot"], chosen["assigned_room"]))
        child_section_schedule.add(
            (chosen["assigned_slot"], chosen["section_id"]))
    return new_child


def mutation(timetable: list, room_pools: dict, room_lookup: dict, professor_pools: dict, all_timeslots: list, slots_to_order_map: dict, mutation_rate: float = 0.02):
    mutated_chromosome = list(timetable)
    """
    Mutates the timetable based on probability.
    Timeslot is mutated by picking a timeslot with least clashes.
    Room is mutated by picking a room with less travel time.
    Professor is mutated byt picking a professor with the lowest current workload.
    """
    prof_load_tracker = defaultdict(int)
    prof_schedule_tracker = defaultdict(list)
    slot_occupancy_tracker = defaultdict(list)
    section_schedule_tracker = defaultdict(list)

    for gene in mutated_chromosome:
        prof_load_tracker[gene['assigned_prof']] += 1
        slot_occupancy_tracker[gene["assigned_slot"]].append(gene)
        prof_schedule_tracker[gene["assigned_prof"]].append(gene)
        section_schedule_tracker[gene["section_id"]].append(gene)

    for i in range(len(mutated_chromosome)):

        if random.random() < mutation_rate:
            single_class = mutated_chromosome[i].copy()
            old_prof = single_class['assigned_prof']
            old_slot = single_class["assigned_slot"]
            random_chance = random.random()

            if random_chance < 0.40:
                best_slot = old_slot
                fewest_clashes = float("inf")

                for _ in range(3):
                    candidate_slot = get_valid_starting_slot(
                        single_class["duration"], all_timeslots)
                    clashes = 0

                    for other_class in slot_occupancy_tracker.get(candidate_slot, []):
                        if other_class["assigned_slot"] == candidate_slot and other_class != single_class:
                            if other_class["assigned_prof"] == single_class["assigned_prof"]:
                                clashes += 1
                            if other_class["assigned_room"] == single_class["assigned_room"]:
                                clashes += 1
                            if other_class["section_id"] == single_class["section_id"]:
                                clashes += 1

                    if clashes < fewest_clashes:
                        fewest_clashes = clashes
                        best_slot = candidate_slot

                    if fewest_clashes == 0:
                        break

                slot_occupancy_tracker[old_slot].remove(single_class)
                single_class["assigned_slot"] = best_slot
                slot_occupancy_tracker[best_slot].append(single_class)

            elif random_chance < 0.70:
                pool_key = get_pool_key(single_class)

                if pool_key and pool_key in room_pools and room_pools[pool_key]:
                    safe_rooms = tuple(room_pools[pool_key])
                    candidate_rooms = random.sample(
                        safe_rooms, min(3, len(safe_rooms)))
                    best_room = candidate_rooms[0]
                    fewest_travel_penalties = float("inf")

                    professor = single_class["assigned_prof"]
                    current_slot_order = slots_to_order_map[single_class["assigned_slot"]]
                    current_duration = single_class["duration"]

                    for room in candidate_rooms:
                        travel_penalty = 0
                        room_obj = room_lookup[room]

                        for other_class in prof_schedule_tracker[professor]:
                            if other_class["assigned_prof"] == professor and single_class != other_class:
                                other_slot_order = slots_to_order_map[other_class["assigned_slot"]]
                                other_duration = other_class["duration"]

                                back_to_back_class = (current_slot_order + current_duration == other_slot_order) or (
                                    other_slot_order + other_duration == current_slot_order)

                                if back_to_back_class:
                                    other_room_obj = room_lookup[other_class["assigned_room"]]

                                    if room_obj.building_block != other_room_obj.building_block:
                                        travel_penalty += 1

                        if travel_penalty < fewest_travel_penalties:
                            fewest_travel_penalties = travel_penalty
                            best_room = room

                        if travel_penalty == 0:
                            break

                    single_class["assigned_room"] = best_room

            else:
                course_id = single_class['course_id']
                prof_load_tracker[old_prof] -= 1
                if course_id in professor_pools:
                    new_prof = min(
                        professor_pools[course_id], key=lambda p: prof_load_tracker[p])
                    single_class["assigned_prof"] = new_prof

            prof_load_tracker[single_class['assigned_prof']] += 1
            mutated_chromosome[i] = single_class

    return mutated_chromosome


def ga_for_dual_delivery(timeslot_df, classes_df, professors_df, rooms_df, status_text=None):
    """
    This is the main genetic algorithm function where the process of initialization, crossover and mutation take place to achieve a feasible solution for University Timetabling in Dual-Delivery envionment.
    The genetic algorithm utilizes parallel processing to evaluate timetables
    """
    POPULATION_SIZE = 150
    MAX_GENERATIONS = 1000
    TOURNAMENT_SIZE = 10

    university_data = load_university_data(
        timeslot_df, classes_df, professors_df, rooms_df)

    if "error" in university_data:
        raise ValueError(university_data["error"])

    genes_list = university_data["genes_list"]
    room_lookup = university_data["room_lookup"]
    room_pools = university_data["room_pools"]
    prof_lookup = university_data["professor_lookup"]
    professor_pools = university_data["professor_pools"]
    all_timeslots = university_data["timeslots"]

    slots_to_day_map = {slot: slot.split("_")[0] for slot in all_timeslots}
    slots_to_order_map = {slot: index for index,
                          slot in enumerate(all_timeslots)}
    order_to_slots_map = {index: slot for index,
                          slot in enumerate(all_timeslots)}

    start_time = time.time()
    ultimate_best_schedule = {}
    ultimate_best_fitness = float('-inf')
    BASE_MUTATION = 0.01
    patience_limit = 50
    generations_without_improvement = 0
    current_mutation_rate = BASE_MUTATION
    previous_ultimate_best = float('-inf')

    population = create_population(
        POPULATION_SIZE, genes_list, all_timeslots, room_pools, professor_pools)

    eval_func = partial(fitness_function,
                        all_timeslots=all_timeslots,
                        room_pools=room_pools,
                        room_lookup=room_lookup,
                        prof_lookup=prof_lookup,
                        slots_to_day_map=slots_to_day_map,
                        slots_to_order_map=slots_to_order_map,
                        order_to_slots_map=order_to_slots_map)

    with concurrent.futures.ProcessPoolExecutor() as executor:

        for generation in range(MAX_GENERATIONS):
            evaluated_population = []

            results = list(executor.map(eval_func, population, chunksize=25))

            for timetable, fitness in zip(population, results):
                fitness = fitness[0] if isinstance(fitness, tuple) else fitness
                evaluated_population.append((timetable, fitness))

                if fitness > ultimate_best_fitness:
                    ultimate_best_schedule = timetable
                    ultimate_best_fitness = fitness

            if ultimate_best_fitness > previous_ultimate_best:
                generations_without_improvement = 0

                previous_ultimate_best = ultimate_best_fitness
                current_mutation_rate = 0.01
            else:
                generations_without_improvement += 1

            if generations_without_improvement >= patience_limit:
                current_mutation_rate = 0.03
                generations_without_improvement = 0
            elif current_mutation_rate == 0.03:
                current_mutation_rate = 0.01

            if generation % 10 == 0:
                if status_text:
                    status_text.info(
                        f"Generation {generation} | Current Best Fitness: {round(ultimate_best_fitness, 4)}")

            new_population = []

            new_population.append(ultimate_best_schedule.copy())
            while len(new_population) < POPULATION_SIZE:
                parent1 = tournament_selection(
                    evaluated_population, TOURNAMENT_SIZE)
                parent2 = tournament_selection(
                    evaluated_population, TOURNAMENT_SIZE)

                new_child = heuristic_crossover(parent1, parent2)
                mutated_child = mutation(
                    new_child, room_pools, room_lookup, professor_pools, all_timeslots, slots_to_order_map, current_mutation_rate)

                new_population.append(mutated_child)

            population = new_population

    end_time = time.time()

    execution_time = end_time-start_time
    minutes = int(execution_time // 60)
    seconds = int(execution_time % 60)

    print(f"Final Best Fitness Score: {round(ultimate_best_fitness, 4)}")
    print(f"Execution time of full cycle: {minutes}:{seconds}")

    return ultimate_best_schedule
