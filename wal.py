# Wrapper around feh to better deal with different
# wallpaper dimensions and preferences

# TODO: eliminate the ugly and confusing globals
import re
import argparse
import subprocess
import base64
import time
import os
from subprocess import Popen
from pathlib import Path
import pandas as pd

# dir = Path("~/Pictures/Wallpapers").expanduser().__str__()
_view = None
_mode = ["", "--no-xinerama"]
_columns = ["Picture", "view", "ignore"]
_path = None

# Hashes given path and uses it as name for new csv
def generate(dir):
    global _path

    hash = base64.b64encode(bytes(dir.expanduser().__str__(), "utf-8")).decode("utf-8")
    path = Path("~/.config/wal/" + hash + ".csv").expanduser()
    _path = path

    print(base64.b64decode(bytes(hash, "utf-8")).decode("utf-8"))

    if Path("~/.config/wal").expanduser().exists() is not True:
        Path("~/.config/wal").expanduser().mkdir()
    if path.exists():
        raise ValueError("CSV for this directory already exists")

    df = pd.DataFrame(columns=_columns)
    df = update(dir, df) # Populate DataFrame
    df.to_csv(path)


# Cull current wallpaper(taken from .fehbg)
def cull(): # TODO: Method to un-cull maybe
    global _path

    df = pd.read_csv(_path, index_col=0)
    dir, (name, hash) = getPaths()
    setAttributes(hash, df, ignore=1)


# Reload current Wallpaper(for usage with -s or -m)
def reload(): # TODO: Will break when neither -s nor -m is given
    global _path
    global _view

    dir, (name, hash) = getPaths()
    print(dir.__str__() + "/" + name)
    df = pd.read_csv(_path, index_col=0)
    p = runfeh(dir, name)
    setAttributes(hash, df)
    return p


# Load new Wallpaper from directory
def newwp():
    global _path
    global _view

    df = pd.read_csv(_path, index_col=0)
    dir, (name, hash) = getPaths()

    if _view is None:
        picture, view, ignore = getAttributes(base64.b64decode(bytes(df.sample(n=1)["Picture"].values[0], "utf-8")).decode("utf-8"), df)
        _view = view

    p = runfeh(dir, base64.b64decode(bytes(df.sample(n=1)["Picture"].values[0], "utf-8")).decode("utf-8"))
    return p


# Given a dir and a DataFrame this will fill the DataFrame with all entries not already in the csv
def update(dir, df):
    path = dir.expanduser()
    items = [x.name for x in path.iterdir() if x.is_file()]

    df2 = pd.concat([pd.DataFrame({"Picture": base64.b64encode(bytes(item, "utf-8")).decode("utf-8"), "view":_view, "ignore":0}, index=[x], columns=_columns) for (x, item) in enumerate(items)], ignore_index=True)
    df = df.append(df2[~df2.isin(df)].dropna())

    return df


# Get image directory and name/hash of current picture
def getPaths():
    global _path
    regex = re.compile(r"'([^']*)'")

    full_path = base64.b64decode(bytes(_path.name.split(".")[0], "utf-8")).decode("utf-8")
    file_name = []
    with open(Path("~/.fehbg").expanduser(), "r") as f:
        text = f.read()
        file_name = regex.findall(text)[0].split("/")[-1]
    file_hash = base64.b64encode(bytes(file_name, "utf-8")).decode("utf-8")

    return full_path, (file_name, file_hash)


# Get attributes of image per the loaded csv
def getAttributes(picture_name, df):
    row = df.loc[df["Picture"] == picture_name].values
    picture, view, ignore  = row[0]
    return picture, view, ignore


# Set attributes of image in the loaded csv
def setAttributes(picture_name, df, *, ignore=None):
    global _view
    global _path

    df.loc[df["Picture"] == picture_name, "view"] = _view
    if ignore is not None:
        df.loc[df["Picture"] == picture_name, "ignore"] = ignore
    df.to_csv(_path)


def runfeh(dir, name):
    if _view == 0:
        p = Popen(["feh", "--bg-scale", dir + "/" + name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while p.poll() is None:
            time.sleep(0.5)
        return p.returncode
    elif _view == 1:
        p = Popen(["feh", "--bg-scale", _mode[_view], dir + "/" + name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while p.poll() is None:
            time.sleep(0.5)
        return p.returncode


def main():
    global _path
    global _view

    parser = argparse.ArgumentParser()
    monitor_group = parser.add_mutually_exclusive_group()
    file_group = parser.add_mutually_exclusive_group()

    monitor_group.add_argument("-s", "--single", help="Display the wallpaper once across all displays", action="store_true")
    monitor_group.add_argument("-m", "--multiple", help="Display the wallpaper for each display", action="store_true")
    file_group.add_argument("-n", "--new", help="Pick a new file", action="store_true")
    file_group.add_argument("-r", "--reload", help="Reload the current wallpaper", action="store_true")
    file_group.add_argument("-c", "--cull", help="Cull wallpaper from the selection and pick a new one", action="store_true")
    file_group.add_argument("-g", "--generate", help="Accepts path to new wallpaper directory and generates a new csv for it", default=None, type=str)

    args = parser.parse_args()

    # _view is set to 0 by default at the top of the file
    # TODO: Don't default so I know what values to actually pull from the csv
    if args.single is True:
        _view = 1
    elif args.multiple is True:
        _view = 0

    for file in Path(os.environ.get("XDG_CONFIG_DIR", "~/.config/wal")).expanduser().glob("*.csv"): # TODO: Mark last modified csv and use it instead of picking the last one the iterator coughs up
        _path = file
    if _path is None and args.generate is None:
        raise ValueError("No configured csv found")

    # TODO: Open DataFrame here and pass with dir Path directly to functions along with view

    if args.new:
        newwp()
    elif args.reload:
        reload()
    elif args.cull:
        cull()
    elif args.generate is not None:
        generate(Path(args.generate))

    # for p in programs:
    #     Popen(['nohup', p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    #     print(f"Started {p}")
    # df = pd.read_csv("~/.config/wal/e11b29f470cd8d2cd6c4c117a4a5dad34a30efb55dbd019d2197d1f24b2383df.csv")
    # print(df.shape)
    # df = update(dir, df)
    # print(df.shape)
    print("Finished")

if __name__ == "__main__":
    main()
