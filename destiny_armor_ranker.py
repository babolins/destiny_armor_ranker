#!/usr/bin/env python

import pandas as pd
import numpy as np
import itertools as it
from pathlib import Path
from argparse import ArgumentParser


def select_armor(data, class_, type_, stat_a, stat_b):
    """
    Select the best legendary armor of a particular class and type with
    stat_a >= stat_b. The "Selected" column of the input DataFrame is modified
    in place. The best piece of armor is the piece with the highest combined
    half tiers of stat_a and stat_b, with ties broken by the total number of
    tiers, the total number of high stats, and the base stat total.

    Parameters:
        data    --  The DataFrame containing armor info, this is modified
        class_  --  The class that can equip the armor
        type_   --  The armor slot
        stat_a  --  the higher stat
        stat_b  --  the lower stat

    Returns:
        None
    """

    data_subset = data.query(
        "Equippable == '{}' & Type == '{}' & Tier == 'Legendary' & `Not Trash`".format(class_, type_)
    ).query(
        "`High {stat_a}` & `High {stat_b}` & `{stat_a} (Base)` >= `{stat_b} (Base)`".format(
            stat_a=stat_a,
            stat_b=stat_b
        ),
    ).copy()

    if len(data_subset.index) > 0:
        data_subset["Score"] = data_subset["{} Tiers".format(stat_a)] + data_subset["{} Tiers".format(stat_b)]

        data_subset.sort_values(
            by=["Score", "Total Tiers", "Total High Stats", "Total (Base)"],
            ascending=False,
            inplace=True
        )

        data.loc[data_subset.iloc[0].name, "Selected"] = True


def process_armor_csv(armor_file, min_tiers, min_stat_total):
    """
    Read a DIM destinyArmor.csv file, determine the best legendary armor
    pieces, and mark the remaining armor pieces as junk. Exotic armor and
    armor more common than legedary armor is not considered. Class armor
    is also ignored.

    Parameters:
        armor_file      --  The path to the DIM destinyArmor.csv file
        min_tiers       --  The minimum number of tiers the top two stats need
                            to have in order for an armor piece to be
                            considered useful
        min_stat_total  --  The minimum base stat total for an armor piece to
                            be considered useful

    Returns:
        None
    """

    _classes = [
        "Hunter",
        "Titan",
        "Warlock"
    ]

    _types = [
        "Helmet",
        "Gauntlets",
        "Chest Armor",
        "Leg Armor",
    ]

    _stats = [
        "Mobility",
        "Resilience",
        "Recovery",
        "Discipline",
        "Intellect",
        "Strength"
    ]

    base_path = Path(armor_file)

    data_orig = pd.read_csv(base_path)
    data = data_orig.copy()

    for stat in _stats:
        data["{} Tiers".format(stat)] = np.floor(data["{} (Base)".format(stat)] * 2 / 10) / 2
        data["High {}".format(stat)] = np.where(data["{} Tiers".format(stat)] >= min_tiers, True, False)

    data["Total Tiers"] = sum(data["{} Tiers".format(stat)] for stat in _stats)
    data["Total High Stats"] = sum(data["High {}".format(stat)] for stat in _stats)
    data["Not Trash"] = (data["Total (Base)"] >= min_stat_total) & (data["Total High Stats"] >= 2)
    data["Selected"] = np.where(data["Tier"] == "Exotic", True, False)

    for c, t in it.product(_classes, _types):
        for a, b in it.permutations(_stats, 2):
            select_armor(data, c, t, a, b)

    junk = data.query(
        "not Selected & Type != 'Hunter Cloak' & Type != 'Titan Mark' & Type != 'Warlock Bond'"
    )
    data_orig.loc[junk.index.values, "Tag"] = "junk"

    data_orig.to_csv(base_path.with_stem(base_path.stem + "_mod"), index=False)

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Select the best legendary armor pieces from a DIM destinyArmor.csv file and tag the rest of the "
                    "pieces as junk. Pieces are selected only if their stat total is above a threshold, and they have "
                    "at least two stats above a second threshold. The pieces with the highest number of half tiers in "
                    "their two highest stats are selected for each slot and combination of stats A and B such that "
                    "stat A > stat B, with ties broken by total number of stat tiers, followed by the total number "
                    "of high stats, and finally by highest base stat total. Class armor and Exotic armor is ignored, "
                    "and armor more common than legendary is automatically marked as junk. A new destinyArmor_mod.csv "
                    "file is output to be re-imported into DIM."
    )
    parser.add_argument("file", metavar="FILE", help="the path to your DIM destinyArmor.csv file")
    parser.add_argument(
        "--min_stat", default=15, type=int,
        help="The minimum stat value that an armor piece must have in two separate stats in order for the armor piece "
             "to be considered a high stat roll, will be rounded down to the nearest multiple of 5 (default: 15)"
    )
    parser.add_argument(
        "--min_stat_total", default=60, type=int,
        help="The minimum base stat total that an armor piece must have in order to be considered useful (default: 60)"
    )

    args = parser.parse_args()

    process_armor_csv(
        args.file,
        min_tiers=np.floor(args.min_stat * 2 / 10) / 2,
        min_stat_total=args.min_stat_total
    )
