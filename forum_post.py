from itertools import cycle
import os
from typing import List, Dict

from ossapi import Ossapi

client_id = int(os.getenv("OSU_CLIENT_ID"))
client_secret = os.getenv("OSU_CLIENT_SECRET")
api = Ossapi(client_id, client_secret)


def get_staff(staff: Dict[str, List[int]]):
    flags = {
        "TR": "https://hey.s-ul.eu/6xt3Mv8G.png",
        "SG": "https://hey.s-ul.eu/qy2hBEEY.png"
    }
    colors = cycle(["[color=#5bba22]", "[color=#b0feb1]"])
    staff_text = ""
    for role, staffers in staff.items():
        users = api.users(staffers)
        staff_text += f"{next(colors)}[b]{role}:[/b][/color] "
        for user in users:
            staff_text += f"[img]{flags[user.country.code]}[/img][url=https://osu.ppy.sh/users/{user.id}][b]{user.username}[/b][/url] "
        staff_text +="\n"

    return staff_text


if __name__ == '__main__':
    staff = {
        "Host": [5642779],
        "Spreadsheet": [3953470],
        "Grafikler": [9143539, 10440852],
        "Mappool": [7537133],
        "Hakemler":[8007528, 13068741, 14684430, 14958380, 6713666, 8128670],
        "Playtester": [14684430, 8128670, 13068741, 18393124],
        "Yayıncı": [5642779, 3953470, 4903088, 17955587]
    }
    print(get_staff(staff))

