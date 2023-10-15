import datetime
import json
import logging
import shutil
import subprocess
import sys
from operator import itemgetter
from pathlib import WindowsPath

from osrparse import Replay
from rosu_pp_py import Beatmap, Calculator
from slider import Beatmap as SliderBeatmap

from utils.osu_db import parse_osu_db


def get_beatmap_spikes(replay, beatmaps, video_len_ms: int = 60000):
    beatmap_hash = replay.beatmap_hash
    beatmap = beatmaps[beatmap_hash]
    beatmap_filepath = WindowsPath("E:\\osu!\\Songs") / beatmap.folder_name / beatmap.name_of_osu_file
    slider_beatmap = SliderBeatmap.from_path(path=str(beatmap_filepath))
    map = Beatmap(path=str(beatmap_filepath))
    calc = Calculator(mods=replay.mods)
    strains = calc.strains(map)
    beatmap_attributes = calc.map_attributes(map)
    video_length = video_len_ms * beatmap_attributes.clock_rate
    spike_begin, spike_end = get_spike_by_continuous_max(slider_beatmap, strains, video_length,
                                                         beatmap_attributes.clock_rate)
    return spike_begin, spike_end


def get_spike_by_continuous_max(beatmap, strains, video_length: int, clock_rate):
    rolling_window_len = int(video_length / strains.section_len)
    total_strains = [sum(x) for x in zip(strains.speed, strains.aim)]

    first_object = beatmap.hit_objects()[0]
    last_object = beatmap.hit_objects()[-1]

    beatmap_begin = first_object.time.total_seconds() * 1000 * clock_rate
    beatmap_end = last_object.time.total_seconds() * 1000 * clock_rate

    rolling_sum_spikes = []
    for i in range(0, len(total_strains) - rolling_window_len):
        rolling_sum_spikes.append(sum(total_strains[i:rolling_window_len + i]))
    spike_index, max_spike = max(enumerate(rolling_sum_spikes), key=itemgetter(1))
    spike_ms = beatmap_begin + int((spike_index + (rolling_window_len / 2)) * strains.section_len)

    return generate_spike_begin_end_from_max(beatmap_begin, beatmap_end, spike_ms, video_length)


def generate_spike_begin_end_from_max(beatmap_begin, beatmap_end, spike_ms, video_length):
    spike_begin = max(beatmap_begin, spike_ms - (video_length / 2))
    spike_end = min(spike_ms + (video_length / 2), beatmap_end)
    if spike_end == beatmap_end:
        spike_begin = max(spike_end - video_length, beatmap_begin)
    elif spike_begin == beatmap_begin:
        spike_end = min(spike_begin + video_length, beatmap_end)
    spike_begin = datetime.timedelta(milliseconds=spike_begin)
    spike_end = datetime.timedelta(milliseconds=spike_end)
    return spike_begin, spike_end


def update_danser_config(replay_mod):
    with open("danser_config.json", "r") as f:
        danser_config = json.load(f)

    mod_colors = {
        "NM": 210,
        "HD": 45,
        "HR": 1,
        "DT": 258,
        "FM": 32,
        "TB": 334,
    }
    danser_config["Gameplay"]["StrainGraph"]["FgColor"]["Hue"] = mod_colors[replay_mod]
    if replay_mod == "TB":
        danser_config["Recording"]["Filters"] = "fade=t=in:st=0:d=2.5,fade=t=out:st=117.5:d=2.5"
        danser_config["Recording"]["AudioFilters"] = "afade=t=in:st=0:d=2.5,afade=t=out:st=117.5:d=2.5"
    else:
        danser_config["Recording"]["Filters"] = "fade=t=in:st=0:d=2.5,fade=t=out:st=57.5:d=2.5"
        danser_config["Recording"]["AudioFilters"] = "afade=t=in:st=0:d=2.5,afade=t=out:st=57.5:d=2.5"

    with open("danser_config.json", "w") as f:
        json.dump(danser_config, f, indent=4)


def copy_danser_config():
    shutil.copyfile("danser_config.json", "C:\\danser\\settings\\danser_config.json")


if __name__ == '__main__':

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(process)d | %(name)s | %(funcName)s | %(message)s',
        datefmt='%d/%m/%Y %I:%M:%S')
    ch.setFormatter(formatter)

    logger.addHandler(ch)

    replays_folder = WindowsPath("replays")
    player_skins = {"Ievi-": "malisz_og",
                    "Lin": "owoLynn",
                    "heyronii": "《CK》 Bacon boi 1.0 『blue』",
                    "Raikouhou": "Aristia(Edit)",
                    "LyeRR": "Aristia Editt",
                    "SunoExy": "Night of Knights",
                    "megumic": "-#KW-! If there was an endpoint.",
                    "garvanturr": "_Shield",
                    "ErAlpha": "-_clackz",
                    "raven waffles": "Unnamed Skin",
                    "Clarz": "-        # WhiteCat (1.0) 『CK』 #-",
                    "kefn": "- JesusOmega {NM} 『Planets』 -",
                    "Orkay": "Vaxei_2023"
                    }
    args = ["danser-cli", "-noupdatecheck", "-record", "-preciseprogress"]
    beatmaps = parse_osu_db("E:\\osu!\\osu!.db")
    for replay_file in replays_folder.glob("*.osr"):
        replay = Replay.from_path(replay_file)
        replay_filename = replay_file.name.replace("_", " ")
        replay_player = " ".join(replay_filename.split(" ")[:-1])
        replay_mod = replay_filename.split(" ")[-1][:2]
        if replay_mod == "TB":
            video_length = "00:02:00"
            spike_begin, spike_end = get_beatmap_spikes(replay, beatmaps, 120000)
        else:
            video_length = "00:01:00"
            spike_begin, spike_end = get_beatmap_spikes(replay, beatmaps)
        replay_skin = player_skins[replay_player]
        video_path = replay_file.stem
        update_danser_config(replay_mod)
        copy_danser_config()
        video_fullpath = WindowsPath(replay_file.with_suffix(".mp4").name)
        extra = ["-replay", f"{replay_file}", "-skin", f"{replay_skin}", "-out", f"{video_path}", "-start",
                 f"{spike_begin.total_seconds()}", "-end", f"{spike_end.total_seconds()}", "-settings=danser_config"]
        final_args = args + extra
        subprocess.run(final_args)

        ffmpeg_args = ["ffmpeg", "-y", "-to", video_length,
                       "-i", f"C:\\danser\\videos\\{video_path}.mp4",
                       "-c:v", "copy", "-c:a", "copy",
                       "-avoid_negative_ts", "1", f"videos/{video_fullpath}"]
        subprocess.run(ffmpeg_args)
