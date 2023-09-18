import copy
import json
import shutil
import statistics
from pathlib import WindowsPath

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', ]

# The ID and range of a sample spreadsheet.
ADMIN_SHEET_ID = '13UbJv82SOhLa2D2UOkQbjkyQc2o9JQGgHW6mCci52Pk'
SCORES_RANGE_NAME = 'Solo Placements!A:ZZ'
TEAMS_RANGE_NAME = 'Teams!A2:B'

MAPPOOL_SHEET_ID = '1GRqeFNixAL_Ngai4m1j20czRMFSF2EJYlW3bqB7cffQ'
MAPPOOL_RANGE_NAMES = ['Ro32!AP3:BC',
                       'Ro16!AP3:BC',
                       'QF!AP3:BC',
                       'SF!AP3:BC',
                       'F!AP3:BC',
                       'GF!AP3:BC']


def get_player_seeds(score_rows, disqualified_players):
    new_seedings = {}
    seed = 1
    for row in score_rows:
        player = row[3]
        player_original_seed = row[1][1:]
        if player in disqualified_players:
            player_seed = "DQF"
        else:
            player_seed = seed
            seed += 1
        new_seedings[player_original_seed] = player_seed

    return new_seedings

def mod_score_calculation(score_rows):
    scores = {"NM": [9+i*4 for i in range(4)],
              "HD": [25+i*4 for i in range(2)],
              "HR": [33+i*4 for i in range(2)],
              "DT": [41+i*4 for i in range(2)]}
    mod_seeds = {"NM": [],
                 "HD": [],
                 "HR": [],
                 "DT": []}
    for mod_name, score_indexes in scores.items():
        mod_scores = [sum([int(scores[idx].replace(',','')) for idx in score_indexes]) for scores in score_rows]
        median = statistics.median(mod_scores)
        mod_algo = lambda x: x/median
        mod_algo_result = [mod_algo(score) for score in mod_scores]
        seeding_indexes = [i for i in sorted(range(len(mod_algo_result)),key=mod_algo_result.__getitem__, reverse=True)]
        seedings = {idx: i+1 for i, idx in enumerate(seeding_indexes)}
        mod_seeds[mod_name] = seedings

    return mod_seeds

def update_teams(sheet, bracket_json):
    score_url = sheet.values().get(spreadsheetId=ADMIN_SHEET_ID,
                                   range=SCORES_RANGE_NAME).execute()
    player_scores = score_url.get('values', [])
    teams_url = sheet.values().get(spreadsheetId=ADMIN_SHEET_ID,
                                   range=TEAMS_RANGE_NAME).execute()
    player_info = teams_url.get('values', [])
    players_by_id = {player[1]: player[0] for player in player_info}
    teams = []
    team_template = {
        "FullName": "",
        "FlagName": "",
        "Acronym": "",
        "Seed": "",
        "LastYearPlacing": 0,
        "Players": [
            {
                "id": 0,
            }
        ],
        "SeedingResults": [
            {
                "Beatmaps": [
                    {
                        "ID": 1,
                        "Seed": 1
                    }
                ],
                "Mod": "NM",
                "Seed": 1
            }
        ]
    }
    mods = {"NM": {"map_count": 4,
                   "map_idx": 0},
            "HD": {"map_count": 2,
                   "map_idx": 4},
            "HR": {"map_count": 2,
                   "map_idx": 6},
            "DT": {"map_count": 2,
                   "map_idx": 8}}
    beatmaps = [
        "4078016",
        "2365928",
        "815857",
        "2615879",
        "2103984",
        "3900789",
        "554287",
        "1764795",
        "1867710",
        "164250",
    ]
    disqualified_players = [
        "Sanctum",
        "Arson1st",
        "Mikasa-"
    ]
    score_rows = player_scores[7:]
    player_seeds = get_player_seeds(score_rows, disqualified_players)
    mod_seedings = mod_score_calculation(score_rows)
    for player_idx, player_row in enumerate(score_rows):
        player_name = player_row[3]
        player_team_dict = copy.deepcopy(team_template)

        player_team_dict["FullName"] = player_name
        player_team_dict["Acronym"] = player_name
        player_team_dict["FlagName"] = "TR"
        player_team_dict["Players"][0]["id"] = players_by_id[player_name]
        player_original_seed = player_row[1][1:]
        player_team_dict["Seed"] = player_seeds[player_original_seed]

        seeding_results = []
        score_row = player_row[8:48]
        for mod_name, mod_details in mods.items():
            map_count = mod_details["map_count"]
            map_idx = mod_details["map_idx"]
            mod_seed = mod_seedings[mod_name][player_idx]
            mod_pool = {"Mod": mod_name,
                        "Seed": mod_seed,
                        "Beatmaps": []}
            for count in range(map_count):
                beatmap_scores = score_row[(map_idx + count) * 4:4 * (map_idx + count + 1)]
                beatmap_seed_str = beatmap_scores[0][1:]
                if beatmap_seed_str == "":
                    beatmap_seed = 0
                else:
                    beatmap_seed = int(beatmap_scores[0][1:])
                beatmap_score = int(beatmap_scores[1].replace(',', ''))
                mod_pool["Beatmaps"].append({"ID": beatmaps[map_idx + count],
                                             "Score": beatmap_score,
                                             "Seed": beatmap_seed})

            seeding_results.append(mod_pool)
        player_team_dict["SeedingResults"] = seeding_results
        teams.append(player_team_dict)

    bracket_json["Teams"] = teams
    return bracket_json


def update_mappool(sheet, bracket_json):
    mappool_dict = {
        "Ro32": {"BestOf": 9,
                 "StartDate": "2023-09-23T00:00:00.0000000+03:00",
                 "Description": "Round of 32"},
        "Ro16": {"BestOf": 9,
                 "StartDate": "2023-09-30T00:00:00.0000000+03:00",
                 "Description": "Round of 16"},
        "QF": {"BestOf": 11,
               "StartDate": "2023-10-07T00:00:00.0000000+03:00",
               "Description": "Quarter Finals"},
        "SF": {"BestOf": 11,
               "StartDate": "2023-10-14T00:00:00.0000000+03:00",
               "Description": "Semi Finals"},
        "F": {"BestOf": 13,
              "StartDate": "2023-10-21T00:00:00.0000000+03:00",
              "Description": "Finals"},
        "GF": {"BestOf": 13,
               "StartDate": "2023-10-28T00:00:00.0000000+03:00",
               "Description": "Grand Finals"},
    }
    round_template = {
        "Name": "Round of 32",
        "Description": "",
        "BestOf": 9,
        "Beatmaps": [],
        "StartDate": "2023-09-17T19:41:41.0677409+02:00",
        "Matches": []}
    rounds = []
    for mappool_range in MAPPOOL_RANGE_NAMES:
        result = sheet.values().get(spreadsheetId=MAPPOOL_SHEET_ID,
                                    range=mappool_range).execute()
        mappool = result.get('values', [])
        beatmaps = []
        for map in mappool:
            try:
                beatmaps.append({"ID": map[2],
                                 "Mods": map[0]})
            except:
                continue
        round_dict = copy.deepcopy(round_template)
        mappool_name = mappool_range.split("!")[0]
        round_dict["Name"] = mappool_name
        round_dict.update(mappool_dict[mappool_name])
        round_dict["Beatmaps"] = beatmaps
        rounds.append(round_dict)

    bracket_json["Rounds"] = rounds
    return bracket_json


if __name__ == '__main__':
    bracket_json_path = WindowsPath.home() / "AppData" / "Roaming" / "osu" / "tournaments" / "default" / "bracket.json"

    shutil.copyfile(bracket_json_path, bracket_json_path.with_name("bracket_old.json"))
    with open(bracket_json_path, "r", encoding="utf-8") as f:
        bracket_json = json.load(f)

    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    bracket_json = update_teams(sheet, bracket_json)
    bracket_json = update_mappool(sheet, bracket_json)

    with open(bracket_json_path, "w", encoding="utf-8") as f:
        json.dump(bracket_json, f)
