# from myriad import MyriadHost
from myriad import myriadhost, LogFileGenerator
import pydub
import argparse
import sys
import time
import os
import os.path
from shutil import move
from subprocess import Popen
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("files", action="store", nargs="*")

parsed_args = parser.parse_args(sys.argv[1:])

audio_files: list = parsed_args.files
if(len(audio_files) % 2 != 0):
    print("Amount of audio files must be divisible by two!")
    exit(1)

# Sort the audio files into the correct order
audio_files = sorted(audio_files)
print("Supplied audio files have been sorted into the following order:")
for f in audio_files:
    print("\t{0}".format(f))

is_correct_order = "-1"
while is_correct_order != "y" and is_correct_order != "n" and is_correct_order != "":
    is_correct_order = input("Is this correct? [Y/n]: ").lower()

if is_correct_order == "n":
    print("Please rename the files so that they can be sorted in filename order.")
    exit(2)

# Determine what time the files are to be scheduled
datetime_start = datetime.now().replace(minute=0, second=0)
date_input = "-1"
while True:
    try:
        time.strptime(date_input, "%Y")
        datetime_start = datetime_start.replace(year=int(date_input))
        break
    except:
        date_input = input("What year is this due to be scheduled? [{0}]: ".format(
            time.strftime("%Y")))
        if not date_input:
            date_input = time.strftime("%Y")

date_input = "-1"
while True:
    try:
        time.strptime(date_input, "%m")
        datetime_start = datetime_start.replace(month=int(date_input))
        break
    except:
        date_input = input("What month is this due to be scheduled? [{0}]: ".format(
            time.strftime("%m")))
        if not date_input:
            date_input = time.strftime("%m")

date_input = "-1"
while True:
    try:
        time.strptime(date_input, "%d")
        datetime_start = datetime_start.replace(day=int(date_input))
        break
    except:
        date_input = input("What day is this due to be scheduled? [{0}]: ".format(
            time.strftime("%d")))
        if not date_input:
            date_input = time.strftime("%d")

date_input = "-1"
while True:
    try:
        time.strptime(date_input, "%H")
        datetime_start = datetime_start.replace(hour=int(date_input))
        break
    except:
        date_input = input("What hour is this due to be scheduled?: ")

presenter_name = ""

while not presenter_name:
    presenter_name = input("Who is presenting this show?: ")

# Rename the audio files to our format
print("Renaming files...")
for i in range(0, len(audio_files)):
    new_file_name = datetime_start.strftime(
        "%Y%m%d-%H00-") + f"{(i+1):02}" + "-" + presenter_name.replace(" ", "") + os.path.splitext(audio_files[i])[1]
    print("Renaming: {0} -> {1}".format(audio_files[i], new_file_name))
    audio_files[i] = move(audio_files[i], os.path.join(
        os.path.dirname(audio_files[i]), new_file_name))

# Convert the audio files to Wav, if necessary
converted_audio_files: list = []

for f in audio_files:
    if not os.path.splitext(f)[1].lower() == ".wav":
        print("Converting to wav file: {0}".format(f))

        proc = Popen(["ffmpeg",
                      "-i", f,
                      "-c:a", "pcm_s16le",
                      "-y",
                      os.path.abspath(os.path.splitext(
                          f)[0] + ".wav")
                      ], shell=True)
        proc.wait()

    converted_audio_files.append(os.path.splitext(f)[0] + ".wav")

# Try to import the carts into Myriad
# First, find the first range of carts free from 1501

myriad_host = myriadhost.MyriadHost("192.168.0.4")

print("Finding free space for carts in AudioWall...")
start_cart = 1501
cart_range_found = False
while not cart_range_found and start_cart < 1600:
    # print("Trying cart {0}".format(start_cart))
    start_result = myriad_host.send("AUDIOWALL CUE 1,{0}".format(start_cart))

    if start_result:  # Cart exists, move on
        start_cart += 1
    else:  # Cart does not exist her, try the next cart
        for i in range(1, len(converted_audio_files) + 1):
            range_result = myriad_host.send(
                "AUDIOWALL CUE 1,{0}".format(start_cart + i))
            if range_result:
                start_cart += i+1
                break

            cart_range_found = True

if cart_range_found:
    print("Found carts: {0}-{1}".format(start_cart,
                                        start_cart+len(converted_audio_files)-1))
else:
    print("No carts available between 1500 and 1600!")
    exit(3)

# Import audio onto audiowall
print("Importing audio to AudioWall...")
for i in range(0, len(audio_files)):
    print(
        f"Importing {os.path.basename(converted_audio_files[i])} to cart {start_cart + i}")
    if not myriad_host.send(
            f"AUDIOWALL IMPORTFILE \"{converted_audio_files[i]}\",{start_cart + i}"):
        print("Failed to import cart!")

# Create log file for hour
print("Creating Myriad Log file...")

with open(os.path.join("C:\\PSquared\\Logs", f'{datetime_start.strftime("MY%y%m%d.LOG")}'), "w") as log_file:
    for i in range(0, len(converted_audio_files), 2):
        log_file.writelines([
            LogFileGenerator.createHourStart(datetime_start.replace(hour=int(
                datetime_start.strftime("%H"))+int(i/2)), f"{presenter_name}'s Pre-Record"), "\n",
            LogFileGenerator.createCmdSetAutoOn(0, 0), "\n",
            LogFileGenerator.createCart(
                1, "RNH NEWS + JINGLE + AD", "RADIO NEWSHUB", 4, 2, 30), "\n",
            LogFileGenerator.createCmdSetAutoOn(0, 0), "\n",
            LogFileGenerator.createCart(
                start_cart+i, f"{presenter_name}'s Pre-Record Part {i+1}", presenter_name, 2, 28, 00), "\n",
            LogFileGenerator.createLink(10, "Station Ident"), "\n",
            LogFileGenerator.createAdBreak(30), "\n",
            LogFileGenerator.createCart(
                14999, "RNH Advert", "Radio Newshub", 2, 0, 30), "\n",
            LogFileGenerator.createLink(10, "Station Ident"), "\n",
            LogFileGenerator.createCart(
                start_cart+i+1, f"{presenter_name}'s Pre-Record Part {i+2}", presenter_name, 2, 28, 00), "\n",
            LogFileGenerator.createLink(10, "Station Ident"), "\n",
            LogFileGenerator.createAdBreak(58), "\n",
            LogFileGenerator.createAbsoluteTime(59, 45), "\n"
        ])