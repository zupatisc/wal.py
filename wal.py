# Wrapper around feh to better deal with different
# wallpaper dimensions and preferences

import re
import argparse
import subprocess
import base64
import time
import os
from subprocess import Popen
from pathlib import Path
import pandas as pd

_columns = ["Picture", "view", "ignore"]
_verbose = False

# Hashes given path and uses it as name for new csv
def generate(*, dir, view, config_dir):

    hash = stringB64(dir.expanduser().__str__())
    path = Path(config_dir + "/" +  hash + ".csv")


    # TODO: Maybe move check and creation of config dir to main
    if Path(config_dir).exists() is not True:
        Path(config_dir).mkdir()
    if path.exists():
        raise ValueError("CSV for this directory already exists")

    # df = pd.DataFrame(columns=_columns)
    df = update(dir=dir.expanduser(), view=view) # Populate DataFrame
    df.to_csv(path)


# Cull current wallpaper(taken from .fehbg)
def cull(*, data_frame, csv_path): # TODO: Method to un-cull maybe

    _, hash = getFileHandles()
    setAttributes(picture_name=hash, data_frame=data_frame, view=None, csv_path=csv_path, ignore=1)


# Reload current Wallpaper(for usage with -s or -m)
def reload(*, data_frame, wallpapers_path, csv_path, view):

    name, hash = getFileHandles()
    if view is None:
        _, view, _ = getAttributes(hash, data_frame)

    p = runfeh(wallpapers_path=wallpapers_path, picture_name=name, view=view)
    setAttributes(picture_name=hash, data_frame=data_frame, view=view, csv_path=csv_path)

    if _verbose:
        print(f"Picture {name} reloaded with view setting {view}")
    return p


# Load new Wallpaper from directory
def newwp(*, data_frame, wallpapers_path, view):

    picture_name = []
    ignore = 1
    while ignore == 1:
        picture_name, local_view, ignore = getAttributes(data_frame.sample(n=1)["Picture"].values[0], data_frame)
        if view is None:
            view = local_view

    p = runfeh(wallpapers_path=wallpapers_path, picture_name=b64String(picture_name), view=view)
    return p


def refresh(*, data_frame, wallpapers_path, view, csv_path):
        df = update(dir=Path(wallpapers_path), view=view)
        updated_df = pd.concat([data_frame, df[~df.isin(data_frame)].dropna()], ignore_index=True)
        updated_df.to_csv(csv_path)


# Given a dir and a DataFrame this will fill the DataFrame with all entries not already in the csv
def update(*, dir, view):
    items = [x.name for x in dir.iterdir() if x.is_file()]

    df2 = pd.concat([pd.DataFrame({"Picture": stringB64(item), "view":view, "ignore":0}, index=[x], columns=_columns) for (x, item) in enumerate(items)], ignore_index=True)
    # df = pd.concat([df, df2[~df2.isin(df)].dropna()], ignore_index=True)
    # df = df.append(df2[~df2.isin(df)].dropna())

    return df2


# Get image directory and name/hash of current picture
def getFileHandles():
    regex = re.compile(r"'([^']*)'")

    file_name = []
    with open(Path("~/.fehbg").expanduser(), "r") as f:
        text = f.read()
        file_name = regex.findall(text)[0].split("/")[-1]
    file_hash = stringB64(file_name)

    return file_name, file_hash


# Get attributes of image per the loaded csv
def getAttributes(picture_name, df):
    row = df.loc[df["Picture"] == picture_name].values
    picture, view, ignore  = row[0]
    return picture, view, ignore


# Set attributes of image in the loaded csv
def setAttributes(*, picture_name, data_frame, view, csv_path, ignore=None):
    if view is not None:
        data_frame.loc[data_frame["Picture"] == picture_name, "view"] = view

    if ignore is not None:
        data_frame.loc[data_frame["Picture"] == picture_name, "ignore"] = ignore
    data_frame.to_csv(csv_path)


def runfeh(*, wallpapers_path, picture_name, view):
    if view == 0:
        p = Popen(["feh", "--bg-scale", wallpapers_path + "/" + picture_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while p.poll() is None:
            time.sleep(0.5)
        return p.returncode
    elif view == 1:
        p = Popen(["feh", "--bg-scale", "--no-xinerama", wallpapers_path + "/" + picture_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while p.poll() is None:
            time.sleep(0.5)
        return p.returncode


# Returns a plain text string from base64
def b64String(input):
    if isinstance(input, str):
        return base64.b64decode(bytes(input, "utf-8")).decode("utf-8")
    elif isinstance(input, pd.DataFrame):
        return base64.b64decode(bytes(input[0], "utf-8")).decode("utf-8")


# Returns base64 encoded string
def stringB64(input):
    return base64.b64encode(bytes(input, "utf-8")).decode("utf-8")


def main():

    parser = argparse.ArgumentParser()
    monitor_group = parser.add_mutually_exclusive_group()
    file_group = parser.add_mutually_exclusive_group()

    monitor_group.add_argument("-s", "--single", help="Display the wallpaper once across all displays", action="store_true")
    monitor_group.add_argument("-m", "--multiple", help="Display the wallpaper for each display", action="store_true")
    file_group.add_argument("-n", "--new", help="Pick a new file", action="store_true")
    file_group.add_argument("-r", "--reload", help="Reload the current wallpaper", action="store_true")
    file_group.add_argument("-c", "--cull", help="Cull wallpaper from the selection and pick a new one", action="store_true")
    file_group.add_argument("-g", "--generate", help="Accepts path to new wallpaper directory and generates a new csv for it", default=None, type=str)
    file_group.add_argument("-u", "--update", help="Update the csv with potential new wallpapers in the directory", action="store_true")
    parser.add_argument("-v", "--verbose", help="Print certain metrics", action="store_true")

    args = parser.parse_args()
    global _verbose
    _verbose = args.verbose

    view = None
    if args.single is True:
        view = 1
    elif args.multiple is True:
        view = 0

    data_frame = []
    wallpapers_path = []
    csv_path = []
    config_dir = Path(os.environ.get("XDG_CONFIG_DIR", "~/.config") + "/wal").expanduser()
    if args.generate is None:
        for file in config_dir.glob("*.csv"): # TODO: Mark last modified csv and use it instead of picking the last one the iterator coughs up
            data_frame = pd.read_csv(file, index_col=0)
            wallpapers_path = b64String(file.name.split(".")[0])
            csv_path = config_dir.__str__() + "/" + file.name
    if data_frame is None and args.generate is None:
        raise ValueError("No configured csv found")

    if _verbose:
        print(f"Chosen csv file: {csv_path}\nWallpaper dir: {wallpapers_path}")

    if args.new:
        newwp(data_frame=data_frame, wallpapers_path=wallpapers_path, view=view)
    elif args.reload:
        reload(data_frame=data_frame, wallpapers_path=wallpapers_path, csv_path=csv_path, view=view)
    elif args.cull:
        cull(data_frame=data_frame, csv_path=csv_path)
    elif args.generate is not None:
        if view is None:
            view = 0
        generate(dir=Path(args.generate), view=view, config_dir=config_dir.__str__())
    elif args.update:
        if view is None:
            view = 0
        refresh(data_frame=data_frame, wallpapers_path=wallpapers_path, view=view, csv_path=csv_path)

    if _verbose:
        print("Finished")
    return 0

if __name__ == "__main__":
    main()
