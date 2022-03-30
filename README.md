# Destiny Armor Ranker

Process DIM destinyArmor.csv files to select only the very best legendary armor pieces so that you can keep your vault
nice and tidy.

## Basic Usage

Download your destinyArmor.csv file from DIM and run the following command from the directory which contains
destiny_armor_ranker.py:

    ./destiny_armor_ranker.py path/to/destinyArmor.csv

Once the program has finished, upload the resulting destinyArmor_mod.csv file to DIM to see all of your suboptimal
armor pieces marked as junk.

## How Does It Work?

The purpose of this program is to find and mark as junk armor pieces which fit the same niche so that you are only left
with the very best armor pieces. What this means is that for a given class and armor slot (e.g. Titan helmets) and a
combination of two stats, stat A and stat B (e.g. resilience and intellect), it will find the best Titan helmet with
high intellect and high resilience and mark all of the similar Titan helmets as junk.

It's important to note now that armor pieces more common than legendary are automatically marked as junk regardless of
stat roll, and Exotic armor pieces are left alone, as are class armor pieces.

## Requirements

Destiny Armor Ranker has been tested using:

* Python 3.9.7
* Pandas 1.3.3
* Numpy 1.21.2
