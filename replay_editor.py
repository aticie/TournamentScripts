import datetime
import math
import random
from enum import Enum
from pathlib import WindowsPath
from typing import List

from osrparse import Replay, ReplayEventOsu, Key
from slider import Beatmap, HitObject, Circle, Slider, Position as SliderPosition
from slider.position import distance

from utils.osu_db import parse_osu_db


def pos_distance(pos1: SliderPosition, pos2: SliderPosition):
    return math.sqrt((pos1.x - pos2.x) ** 2 + (pos1.y - pos2.y) ** 2)


def diff_pos(pos1: SliderPosition, pos2: SliderPosition):
    return SliderPosition(pos1.x - pos2.x, pos1.y - pos2.y)


def scale_pos(pos: SliderPosition, ratio: float):
    return SliderPosition(pos.x * ratio, pos.y * ratio)


def find_position_change_by_ratio(position1: SliderPosition, position2: SliderPosition, ratio: float):
    delta_pos = diff_pos(position1, position2)
    pos_diff = scale_pos(delta_pos, ratio)
    return diff_pos(delta_pos, pos_diff)


class HitGrade(Enum):
    Hit300 = 300
    Hit100 = 100
    Hit50 = 50
    HitMiss = 0


class MissVerdict(Enum):
    AimMiss = 0
    TimingMiss = 1


class HitEvent:
    def __init__(self, time: datetime.timedelta, keys: Key, position: SliderPosition, replay_event_idx: int):
        self.time = time
        self.keys = keys
        self.position = position
        self.replay_event_idx = replay_event_idx

    @classmethod
    def from_event(cls, event: ReplayEventOsu, absolute_time: datetime.timedelta, replay_event_idx: int):
        return cls(time=absolute_time,
                   keys=event.keys,
                   position=SliderPosition(event.x, event.y),
                   replay_event_idx=replay_event_idx)

    def __repr__(self):
        return f"Hit Event at {self.time} - {self.keys}"


class SuccessfulHitEvent(HitEvent):
    def __init__(self, time: datetime.timedelta, keys: Key, position: SliderPosition, grade: HitGrade,
                 hit_object: HitObject,
                 replay_event_idx: int):
        super().__init__(time, keys, position=position, replay_event_idx=replay_event_idx)
        self.grade = grade
        self.hit_object = hit_object
        self.time_offset = abs(hit_object.time - time)
        self.aim_offset = distance(self.position, hit_object.position)

    def __repr__(self):
        return f"{self.grade} Event at {self.time}: " \
               f"{self.hit_object.__class__.__name__}, {self.hit_object.time} - " \
               f"TimeDiff: {self.time_offset} - AimDiff: {self.aim_offset}"


class MissedHitEvent(SuccessfulHitEvent):
    def __init__(self, time: datetime.timedelta, keys: Key, position: SliderPosition, hit_object: HitObject,
                 replay_event_idx: int, verdict: MissVerdict):
        super().__init__(time=time,
                         keys=keys,
                         position=position,
                         grade=HitGrade.HitMiss,
                         hit_object=hit_object,
                         replay_event_idx=replay_event_idx)
        self.verdict = verdict


def gather_hit_events(replay: Replay) -> list[HitEvent]:
    hit_events = []
    prev_m1_state = 0
    prev_m2_state = 0
    replay_time = 0
    for event_idx, event in enumerate(replay.replay_data):
        replay_time += event.time_delta

        replay_keys = event.keys
        m1_state = replay_keys & 0x1
        m2_state = replay_keys & 0x2

        if m1_state > prev_m1_state or m2_state > prev_m2_state:
            hit_events.append(HitEvent.from_event(event=event,
                                                  absolute_time=datetime.timedelta(milliseconds=replay_time),
                                                  replay_event_idx=event_idx))

        prev_m1_state = replay_keys & 0x1
        prev_m2_state = replay_keys & 0x2

    return hit_events


def diff_rate(diff: float, min: float, mid: float, max: float) -> float:
    if diff > 5:
        return mid + (max - mid) * (diff - 5) / 5

    if diff < 5:
        return mid - (mid - min) * (5 - diff) / 5

    return mid


def get_hit_result(hit_events: List[HitEvent], beatmap: Beatmap, replay: Replay):
    next_hitobject_idx = 0
    next_hit_event_idx = 0

    hit_objects = beatmap.hit_objects()

    mods = {"easy": replay.mods & 2 ** 1,
            "hard_rock": replay.mods & 2 ** 4}
    is_sv2 = replay.mods & 2 ** 29
    od = beatmap.od(**mods)
    cs = beatmap.cs(**mods)
    beatmap_50_window = datetime.timedelta(milliseconds=math.floor(diff_rate(od, 200, 150, 100)))
    beatmap_100_window = datetime.timedelta(milliseconds=math.floor(diff_rate(od, 140, 100, 60)))
    beatmap_300_window = datetime.timedelta(milliseconds=math.floor(diff_rate(od, 80, 50, 20)))
    circle_radius = diff_rate(cs, 54.4, 32, 9.6)
    circle_radius = circle_radius * 1.00041
    print("Hit Windows:")
    print(f"300: {beatmap_300_window}")
    print(f"100: {beatmap_100_window}")
    print(f"50: {beatmap_50_window}")
    print(f"Circle Radius: {circle_radius}")
    object_hit_events = []

    while next_hitobject_idx < len(hit_objects) and \
            next_hit_event_idx < len(hit_events):
        hit_object = hit_objects[next_hitobject_idx]
        hit_event = hit_events[next_hit_event_idx]
        hit_time = hit_event.time

        hitobject_time = hit_object.time
        hitobject_min_time = hitobject_time - beatmap_50_window
        hitobject_max_time = hitobject_time + beatmap_50_window

        if hit_time < hitobject_min_time:
            next_hit_event_idx += 1
            continue
        elif hit_time > hitobject_max_time:
            if isinstance(hit_object, Circle):
                next_hitobject_idx += 1
            object_hit_event = MissedHitEvent(**vars(hit_event), hit_object=hit_object, verdict=MissVerdict.TimingMiss)
        else:
            hit_grade = HitGrade.HitMiss
            if isinstance(hit_object, Circle) or (isinstance(hit_object, Slider) and is_sv2):
                if pos_distance(hit_event.position, hit_object.position) > circle_radius:
                    object_hit_event = MissedHitEvent(**vars(hit_event),
                                                      hit_object=hit_object,
                                                      verdict=MissVerdict.AimMiss)
                else:
                    hit_offset = abs(hit_object.time - hit_event.time)
                    if hit_offset < beatmap_300_window:
                        hit_grade = HitGrade.Hit300
                    elif hit_offset < beatmap_100_window:
                        hit_grade = HitGrade.Hit100
                    elif hit_offset < beatmap_50_window:
                        hit_grade = HitGrade.Hit50
                    else:
                        print(f"There is an error in the code.")

                    object_hit_event = SuccessfulHitEvent(**vars(hit_event),
                                                          grade=hit_grade,
                                                          hit_object=hit_object)
            else:
                if isinstance(hit_object, Slider) and \
                        pos_distance(hit_event.position, hit_object.position) > circle_radius:
                    object_hit_event = MissedHitEvent(**vars(hit_event),
                                                      hit_object=hit_object,
                                                      verdict=MissVerdict.AimMiss)
                else:
                    hit_grade = HitGrade.Hit300
                    object_hit_event = SuccessfulHitEvent(**vars(hit_event),
                                                          grade=hit_grade,
                                                          hit_object=hit_object)
        object_hit_events.append(object_hit_event)
        next_hit_event_idx += 1
        next_hitobject_idx += 1

    return object_hit_events


def correct_miss_event(hit_event: MissedHitEvent, replay: Replay, circle_radius: float):
    print(f"Aim correction for {hit_event}.")
    hit_diff = pos_distance(hit_event.hit_object.position, hit_event.position)
    valid_ratio = circle_radius / hit_diff
    corrected_aim_diff_ratio = (random.random() / 2 + 0.5) * valid_ratio
    print(
        f"New corrected aim diff: {corrected_aim_diff_ratio:.2f}\n"
        f"New diff: {circle_radius / corrected_aim_diff_ratio:.2f}"
    )

    brush_radius = random.randint(12, 18)
    hit_object_position = hit_event.hit_object.position
    cursor_position = hit_event.position
    pos_change = find_position_change_by_ratio(hit_object_position, cursor_position, corrected_aim_diff_ratio)
    replay.replay_data[hit_event.replay_event_idx].x += pos_change.x
    replay.replay_data[hit_event.replay_event_idx].y += pos_change.y
    pull_power = random.random() / 10 + 0.8
    for i in range(1, brush_radius):
        prev_frame_idx = hit_event.replay_event_idx - i
        next_frame_idx = hit_event.replay_event_idx + i
        current_pull_power = math.pow(pull_power, i * 1.2)
        replay.replay_data[prev_frame_idx].x += pos_change.x * current_pull_power
        replay.replay_data[next_frame_idx].x += pos_change.x * current_pull_power
        replay.replay_data[prev_frame_idx].y += pos_change.y * current_pull_power
        replay.replay_data[next_frame_idx].y += pos_change.y * current_pull_power

    replay.count_miss = max(0, replay.count_miss - 1)
    replay.count_300 += 1
    return replay


def fix_replay_scorev2(replay: Replay, object_hit_events: List[HitEvent], beatmap: Beatmap):
    replay_accuracy = (replay.count_300 + replay.count_100 * 100 / 300 + replay.count_50 * 50 / 300) / (
            replay.count_300 + replay.count_100 + replay.count_50 + replay.count_miss)
    accuracy_portion = 0.3
    combo_portion = 0.7

    combo = 0
    max_combo = 0
    for hit_event in object_hit_events:
        if hit_event.grade == HitGrade.HitMiss:
            if combo > max_combo:
                max_combo = combo

            combo = 0
        else:
            combo += 1

    if combo > max_combo:
        max_combo = combo
    total_score = 1000000 * (
            (replay_accuracy * accuracy_portion) + (max_combo / beatmap.max_combo) * combo_portion)
    replay.score = int(total_score)
    return max_combo, total_score


def fix_replay_score(replay: Replay, object_hit_events: List[HitEvent], beatmap: Beatmap):
    score = 0
    combo = 0
    max_combo = 0
    mods = {"easy": replay.mods & 2 ** 1,
            "hard_rock": replay.mods & 2 ** 4}
    mod_multipliers = {2 ** 1: 0.5,  # Easy
                       2 ** 4: 1.06,  # Hard Rock
                       2 ** 3: 1.06,  # Hidden
                       2 ** 10: 1.12,  # Flashlight
                       2 ** 6: 1.12,  # Double Time
                       2 ** 8: 0.3  # Half Time
                       }

    mod_multiplier = 1
    for k, v in mod_multipliers.items():
        if replay.mods & k:
            mod_multiplier *= v
    hp = beatmap.hp(**mods)
    od = beatmap.od(**mods)
    cs = beatmap.cs(**mods)
    hit_objects = beatmap.hit_objects()
    hit_object_count = len(hit_objects)
    drain_time = (hit_objects[-1].time - hit_objects[0].time).total_seconds()
    diff_multiplier = round(hp + cs + od + max(min(hit_object_count / drain_time * 8, 16), 0) / 38 * 5)

    for hit_event in object_hit_events:
        score += int(hit_event.grade.value * (1 + (combo * diff_multiplier * mod_multiplier / 25)))
        if hit_event.grade == HitGrade.HitMiss:
            if combo > max_combo:
                max_combo = combo
            combo = 0
        else:
            combo += 1
    if combo > max_combo:
        max_combo = combo
    replay.score = int(score)
    replay.max_combo = int(max_combo)
    return max_combo, score


def fix_replay_combo(replay: Replay, beatmap: Beatmap):
    replay.max_combo = beatmap.max_combo


def add_mods(replay):
    #replay.mods |= 2**6
    #replay.mods |= 2**3
    pass

if __name__ == '__main__':
    beatmaps = parse_osu_db("E:\\osu!\\osu!.db")
    replays_folder = WindowsPath("replays")
    replay_file = list(replays_folder.glob("*.osr"))[0]
    replay = Replay.from_path(replay_file)
    print(f"Loaded replay file: {replay_file}")

    beatmap_meta = beatmaps[replay.beatmap_hash]
    beatmap_filepath = WindowsPath("E:\\osu!\\Songs") / beatmap_meta.folder_name / beatmap_meta.name_of_osu_file
    beatmap = Beatmap.from_path(path=str(beatmap_filepath))

    hit_events = gather_hit_events(replay)
    object_hit_events = get_hit_result(hit_events=hit_events,
                                       beatmap=beatmap,
                                       replay=replay)

    corrected_replay = replay
    for hit_event in object_hit_events:
        if isinstance(hit_event, MissedHitEvent) and hit_event.verdict == MissVerdict.AimMiss:
            mods = {"easy": replay.mods & 2 ** 1,
                    "hard_rock": replay.mods & 2 ** 4}
            cs = beatmap.cs(**mods)
            circle_radius = diff_rate(cs, 54.4, 32, 9.6)
            corrected_replay = correct_miss_event(hit_event, replay, circle_radius)

    add_mods(replay)
    if replay.mods & 2 ** 29:
        max_combo, score = fix_replay_scorev2(replay, object_hit_events, beatmap)
    else:
        max_combo, score = fix_replay_score(replay, object_hit_events, beatmap)

    fix_replay_combo(replay, beatmap)
    corrected_replay.write_path(replay_file.with_stem(replay_file.stem + "_corrected"))
