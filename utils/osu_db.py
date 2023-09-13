import logging

from utils.primitives import osuString, ByteInt, ByteFloat, IntDoublePairs, ByteDouble

logger = logging.getLogger(__name__)


class Beatmap:
    def __init__(self, file_handle):
        self.artist_name = osuString(file_handle)
        self.artist_unicode = osuString(file_handle)
        self.title = osuString(file_handle)
        self.title_unicode = osuString(file_handle)
        self.creator = osuString(file_handle)
        self.difficulty = osuString(file_handle)
        self.audio_file = osuString(file_handle)
        self.md5_hash = osuString(file_handle)
        self.name_of_osu_file = osuString(file_handle)
        self.ranked_status = ByteInt(file_handle.read(1))  # Ranked status
        self.hc = ByteInt(file_handle.read(2))  # Number of hitcircles
        self.slider = ByteInt(file_handle.read(2))  # Number of sliders
        self.spinner = ByteInt(file_handle.read(2))  # Number of spinners
        self.last_modified = ByteInt(file_handle.read(8))  # Last modification time
        self.ar = ByteFloat(file_handle.read(4))  # Approach rate
        self.cs = ByteFloat(file_handle.read(4))  # Circle size
        self.hp = ByteFloat(file_handle.read(4))  # HP drain
        self.od = ByteFloat(file_handle.read(4))  # Overall difficulty
        self.sv = ByteDouble(file_handle.read(8))  # Slider velocity
        IntDoublePairs(file_handle)
        IntDoublePairs(file_handle)
        IntDoublePairs(file_handle)
        IntDoublePairs(file_handle)
        self.drain_time = ByteInt(file_handle.read(4))  # Drain time
        self.total_time = ByteInt(file_handle.read(4))  # Total time
        self.preview_time = ByteInt(file_handle.read(4))  # Preview time
        nr_of_timings = ByteInt(file_handle.read(4))
        for _ in range(nr_of_timings):
            _ = file_handle.read(17)

        self.beatmap_id = ByteInt(file_handle.read(4))  # Difficulty id
        self.beatmapset_id = ByteInt(file_handle.read(4))  # Difficulty id

        self.thread_id = file_handle.read(4)  # Thread ID
        _ = file_handle.read(4)  # Grades

        """
        Short	Local beatmap offset
        Single	Stack leniency
        Byte	osu! gameplay mode. 0x00 = osu!，0x01 = osu!taiko，0x02 = osu!catch，0x03 = osu!mania
        String	Song source
        String	Song tags
        Short	Online offset
        String	Font used for the title of the song
        Boolean	Is beatmap unplayed
        Long	Last time when beatmap was played
        Boolean	Is the beatmap osz2
        String	Folder name of the beatmap, relative to Songs folder
        Long	Last time when beatmap was checked against osu! repository
        Boolean	Ignore beatmap sound
        Boolean	Ignore beatmap skin
        Boolean	Disable storyboard
        Boolean	Disable video
        Boolean	Visual override
        Short?	Unknown. Only present if version is less than 20140609.
        Int	Last modification time (?)
        Byte	Mania scroll speed
        """
        _ = file_handle.read(2)  # Offset
        _ = file_handle.read(4)  # Leniency
        _ = file_handle.read(1)  # Mode
        _ = osuString(file_handle)  # Source
        _ = osuString(file_handle)  # tags
        _ = file_handle.read(2)  # Online Offset
        _ = osuString(file_handle)  # Font
        _ = file_handle.read(1)  # Unplayed
        _ = file_handle.read(8)  # Last played
        _ = file_handle.read(1)  # Is osz2?
        self.folder_name = osuString(file_handle)  # Folder name
        _ = file_handle.read(8)  # Last checked
        _ = file_handle.read(1)  # Ignore sound
        _ = file_handle.read(1)  # Ignore skin
        _ = file_handle.read(1)  # Ignore sb
        _ = file_handle.read(1)  # Ignore video
        _ = file_handle.read(1)  # Visual override
        _ = file_handle.read(4)  # Last Modification
        _ = file_handle.read(1)  # Mania scroll speed

    def __hash__(self):
        return hash(self.md5_hash)


def parse_osu_db(db_path):
    with open(db_path, 'rb') as f:
        osu_version = ByteInt(f.read(4))
        folder_count = ByteInt(f.read(4))
        account_unlocked = ByteInt(f.read(1))
        date_unlocked = ByteInt(f.read(8))
        player_name = osuString(f)
        num_beatmaps = ByteInt(f.read(4))

        beatmaps = dict()
        for beatmap_no in range(num_beatmaps):
            beatmap = Beatmap(f)
            beatmaps[beatmap.md5_hash] = beatmap
            if beatmap_no % 500 == 0:
                logger.info(f"Parsed {beatmap_no} beatmaps.")

    return beatmaps
