#!/usr/bin/env python

import pandas as pd
import numpy as np
import itertools as it
from pathlib import Path
from argparse import ArgumentParser
from scipy.sparse import csr_matrix, csc_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching, min_weight_full_bipartite_matching
from scipy.optimize import linear_sum_assignment


def select_armor(data, class_, type_, combos, N):
    """
    Select the best legendary armor of a particular class and type by assigning
    armor pieces to various categories corresponding to particular stat combos.
    Then an attempt is made to optimally find the top N armor pieces in each
    category by ranking the sum of the top 2 stat values, the top stat value,
    the sum of the top 3 stat values, and the base stat total and using the
    resulting ranks as weights in a bipartite matching problem.

    Parameters:
        data    --  The DataFrame containing armor info, this is modified
        class_  --  The class that can equip the armor
        type_   --  The armor slot
        combos  --  The stat combos that are considered important
        N       --  The number of armor pieces to keep

    Returns:
        None
    """

    data_subset = data.query(
        "Equippable == '{}' & Type == '{}' & Tier == 'Legendary' & `Not Trash`".format(class_, type_)
    ).copy()

    data_subset.sort_values(
        by=["Top 2", "Top 1", "Top 3", "Total (Base)"],
        ascending=False,
        inplace=True
    )
    data_subset["Rank"] = np.arange(len(data_subset))[::-1] + 1

    labels = ["{}_{}".format(stat_a, stat_b) for stat_a, stat_b in combos]
    for label, (stat_a, stat_b) in zip(labels, combos):
        data_subset[label] = data_subset["High {}".format(stat_a)] & data_subset["High {}".format(stat_b)]

    columns = {label: [i * N + j for j in range(N)] for i, label in enumerate(labels)}
    row_ind, col_ind, mat_dat = [], [], []
    for col in data_subset[labels]:
        for i, (idx, val) in enumerate(data_subset[col].items()):
            if val:
                for j in columns[col]:
                    row_ind.append(i)
                    col_ind.append(j)
                    mat_dat.append(data_subset.loc[idx, "Rank"])
    graph = csr_matrix((mat_dat, (row_ind, col_ind)), shape=(len(data_subset), 2 * len(labels)))

    matching = maximum_bipartite_matching(graph)
    empty_cols, = np.where(matching < 0)

    if len(empty_cols) > 0:
        remaining_cols = np.array([i for i in range(graph.shape[1]) if i not in empty_cols])
        graph = csr_matrix(csc_matrix(graph)[:, remaining_cols])

    row_ind, col_ind = min_weight_full_bipartite_matching(graph, maximize=True)

    for i in row_ind:
        data.loc[data_subset.iloc[i].name, "Selected"] = True


def process_armor_csv(armor_file, min_points, point_threshold, min_stat_total, N):
    """
    Read a DIM destinyArmor.csv file, determine the best legendary armor
    pieces, and mark the remaining armor pieces as junk. Exotic armor and
    armor more common than legedary armor is not considered. Class armor
    is also ignored.

    Parameters:
        armor_file      --  The path to the DIM destinyArmor.csv file
        min_points      --  The minimum number of points the top two stats need
                            to have in order for an armor piece to be
                            considered high stat
        point_threshold --  The minimum threshold for the top stat to be
                            considered a useful roll
        min_stat_total  --  The minimum base stat total for an armor piece to
                            be considered useful
        N               --  The number of pieces from each class-specific stat
                            combo to keep

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

    _block_a = [
        "Mobility",
        "Resilience",
        "Recovery"
    ]

    _block_b = [
        "Discipline",
        "Intellect",
        "Strength"
    ]

    _stats = _block_a + _block_b

    _combos = [(stat_a, stat_b) for stat_a, stat_b in it.product(_block_a, _block_b)]

    _class_combos = {
        "Hunter": _combos,
        "Titan": _combos,
        "Warlock": _combos
    }

    base_path = Path(armor_file)

    data_orig = pd.read_csv(base_path)
    data = data_orig.copy()

    for stat in _stats:
        data["High {}".format(stat)] = (data["{} (Base)".format(stat)] >= min_points)

    df = data[["{} (Base)".format(stat) for stat in _stats]].apply(lambda x: np.sort(x)[::-1], axis=1)
    for i in range(1, 4):
        data["Top {}".format(i)] = df.apply(lambda x: x[:i]).apply(np.sum)

    data["Total High Stats"] = sum(data["High {}".format(stat)] for stat in _stats)
    data["Not Trash"] = (
        (data["Total (Base)"] >= min_stat_total) &
        (data["Total High Stats"] >= 2) &
        (data["Top 1"] >= point_threshold) &
        (data["Top 2"] >= (point_threshold + min_points))
    )
    data["Selected"] = (data["Tier"] == "Exotic")

    for c, t in it.product(_classes, _types):
        select_armor(data, c, t, _class_combos[c], N)

    junk = data.query(
        "not Selected & Type != 'Hunter Cloak' & Type != 'Titan Mark' & Type != 'Warlock Bond'"
    )
    data_orig.loc[junk.index.values, "Tag"] = "junk"

    data_orig.to_csv(base_path.with_stem(base_path.stem + "_mod"), index=False)

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Select the best legendary armor pieces from a DIM destinyArmor.csv file and tag the rest of the "
                    "pieces as junk. Pieces are selected only if their stat total is above a threshold, and they have "
                    "at least two stats above a second threshold. Armor is ranked by the sum of the top to base stat "
                    "values, with ties broken by the top base stat value, then the sum of the top 3 base stat values "
                    "and finally the overall base stat total and the ranks are used to try to optimally assign armor "
                    "to categories that correspond to class-specific binary stat combos based on whether they have "
                    "high values of those stats. Class armor and Exotic armor is ignored, and armor more common than "
                    "legendary is automatically marked as junk. A new destinyArmor_mod.csv file is output to be "
                    "re-imported into DIM."
    )
    parser.add_argument("file", metavar="FILE", help="the path to your DIM destinyArmor.csv file")
    parser.add_argument(
        "--min_points", default=10, type=int,
        help="The minimum stat value that an armor piece must have in two separate stats in order for the armor piece "
             "to be considered a high stat roll"
    )
    parser.add_argument(
        "--point_threshold", default=15, type=int,
        help="The minimum stat value that an armor piece must have in its higher stat to be considered high stat"
    )
    parser.add_argument(
        "--min_stat_total", default=62, type=int,
        help="The minimum base stat total that an armor piece must have in order to be considered useful"
    )
    parser.add_argument(
        "--num", default=2, type=int,
        help="The number of armor pieces from each category to keep"
    )

    args = parser.parse_args()

    process_armor_csv(
        args.file,
        args.min_points,
        args.point_threshold,
        args.min_stat_total,
        args.num
    )
