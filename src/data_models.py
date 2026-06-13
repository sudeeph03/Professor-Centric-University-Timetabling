from dataclasses import dataclass
from typing import List


@dataclass
class Room:
    room_id: str
    r_type: str
    building_block: str
    floor: int

    def __post_init__(self):
        object.__setattr__(self, 'room_id', str(self.room_id).strip())
        object.__setattr__(self, 'building_block', str(
            self.building_block).strip().upper())
        object.__setattr__(self, 'floor', int(str(self.floor).strip()))


@dataclass
class Professor:
    prof_id: str
    prof_name: str
    qualified_courses: List[str]
    max_daily_workload: int
    min_daily_workload: int
    preferred_online_days: List[str]
    unavailable_slots: List[str]
    disliked_slots: List[str]
    weekly_max_load: int
    weekly_min_load: int

    def __post_init__(self):
        object.__setattr__(self, 'prof_id', str(self.prof_id).strip())
        object.__setattr__(self, 'prof_name', str(self.prof_name).strip())
        object.__setattr__(self, 'max_daily_workload',
                           int(self.max_daily_workload))
