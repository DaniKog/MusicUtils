#bpm finder based on the work of David
#https://github.com/scaperot/the-BPM-detector-python

# coding: utf-8-sig
global_encoding = 'utf-8-sig'
import argparse
import math
import taglib
import numpy
import pywt
import csv
from scipy import signal
from scipy.io import wavfile
from os import walk
from os import path

def read_wav(filename):
    # open file, get metadata for audio
    fs = 0
    nsamps = 0
    
    try:
        fs, nsamps =  wavfile.read(filename)
    except IOError as e:
        print(e)
        return
    assert fs > 0

    # Read entire file and make into an array
    samps = nsamps.tolist()
    assert len(samps) > 0 

    sequence_samples = []
    for sampleset in samps:
        for sample in sampleset:
            sequence_samples.append(sample)


    return sequence_samples, fs


# print an error when no data can be found
def no_audio_data():
    print("No audio data for sample, skipping...")
    return None, None


# simple peak detection
def peak_detect(data):
    max_val = numpy.amax(abs(data))
    peak_ndx = numpy.where(data == max_val)
    if len(peak_ndx[0]) == 0:  # if nothing found then the max must be negative
        peak_ndx = numpy.where(data == -max_val)
    return peak_ndx


def bpm_detector(data, fs):
    cA = []
    cD = []
    correl = []
    cD_sum = []
    levels = 4
    max_decimation = 2 ** (levels - 1)
    min_ndx = math.floor(60.0 / 220 * (fs / max_decimation))
    max_ndx = math.floor(60.0 / 40 * (fs / max_decimation))

    for loop in range(0, levels):
        cD = []
        # 1) DWT
        if loop == 0:
            [cA, cD] = pywt.dwt(data, "db4")
            cD_minlen = len(cD) / max_decimation + 1
            cD_sum = numpy.zeros(math.floor(cD_minlen))
        else:
            [cA, cD] = pywt.dwt(cA, "db4")

        # 2) Filter
        cD = signal.lfilter([0.01], [1 - 0.99], cD)

        # 4) Subtract out the mean.

        # 5) Decimate for reconstruction later.
        cD = abs(cD[:: (2 ** (levels - loop - 1))])
        cD = cD - numpy.mean(cD)

        # 6) Recombine the signal before ACF
        #    Essentially, each level the detail coefs (i.e. the HPF values) are concatenated to the beginning of the array
        cD_sum = cD[0 : math.floor(cD_minlen)] + cD_sum

    if [b for b in cA if b != 0.0] == []:
        return no_audio_data()

    # Adding in the approximate data as well...
    cA = signal.lfilter([0.01], [1 - 0.99], cA)
    cA = abs(cA)
    cA = cA - numpy.mean(cA)
    cD_sum = cA[0 : math.floor(cD_minlen)] + cD_sum

    # ACF
    correl = numpy.correlate(cD_sum, cD_sum, "full")

    midpoint = math.floor(len(correl) / 2)
    correl_midpoint_tmp = correl[midpoint:]

    peak_ndx = peak_detect(correl_midpoint_tmp[min_ndx:max_ndx])
    if len(peak_ndx) > 1:
        return no_audio_data()

    peak_ndx_adjusted = peak_ndx[0] + min_ndx
    bpm = 60.0 / peak_ndx_adjusted * (fs / max_decimation)
    return bpm, correl

def process_file(filepath, filename):
    samps, fs = read_wav(str(filepath))

    data = []
    correl = []
    bpm = 0
    n = 0
    nsamps = len(samps)
    window_samps = int(args.window * fs)
    samps_ndx = 0  # First sample in window_ndx
    max_window_ndx = math.floor(nsamps / window_samps)
    bpms = numpy.zeros(max_window_ndx)

    # Iterate through all windows
    for window_ndx in range(0, max_window_ndx):

        # Get a new set of samples
        # print(n,":",len(bpms),":",max_window_ndx_int,":",fs,":",nsamps,":",samps_ndx)
        data = samps[samps_ndx : samps_ndx + window_samps]

        if not ((len(data) % window_samps) == 0):
            raise AssertionError(str(len(data)))

        max_val = abs(max(data, key=abs))
        if max_val > 20000: #ignore quite parts
            bpm, correl_temp = bpm_detector(data, fs)
            if bpm is None:
                continue
            bpms[n] = bpm
            correl = correl_temp
            n = n + 1

        # Iterate at the end of the loop
        samps_ndx = samps_ndx + window_samps

    bpm = numpy.median(bpms)
    bpm = round(bpm,1)
    post_decimal = bpm % 1
    if post_decimal != 5:
        bpm = round(bpm)

    return bpm

def read_existiing_csv(csv_path):
    exiting_files = {}
    if path.isfile(csv_path):
        with open(csv_path, encoding = global_encoding) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                exiting_files[row['FileName']] = { 'Title': row['Title'], 'BPM': row['BPM'], 'Key': row['Key'], 'Path': row['Path']}
    return exiting_files

def record_file_info(filename, filepath, exiting_files):
    csv_entry = {}
    bpm = None
    key = ''
    title, _ = path.splitext(filename)
    # if file already processed

    if filename in exiting_files:
        bpm = exiting_files[filename]["BPM"]
        key = exiting_files[filename]["Key"]
        title = exiting_files[filename]["Title"]
        #ensure file holds right info
        try:
            with taglib.File(filepath, save_on_exit=True) as track:
                ## Update Key
                if 'COMMENT' in track.tags:
                    file_key = track.tags['COMMENT'][0]
                    if key != file_key:
                        if key == '':
                            file_key = track.tags['COMMENT'][0]
                            print(f'Key was incorrect in csv {key} updated to {file_key} from file {filename}')
                            key = file_key # the correct key is from the file
                        else:
                            track.tags['COMMENT'][0] = key
                            print(f'Key was incorrect in file {filename} updated to {key} from csv')

                elif key == '':
                    track.tags['COMMENT'] = [key]
                    print(f'Key was missing in file {filename} updated to {key} from csv')
                ## update BPM
                if track.tags.get("BPM") is None or bpm != track.tags["BPM"][0]:
                    track.tags["BPM"] = bpm
                    print(f'BPM was incorrect in file {filename} updated to {bpm}')
                ## update TITLE  
                if track.tags.get("TITLE") is None or title != track.tags["TITLE"][0]:
                    title_from_file = track.tags["TITLE"]
                    track.tags["TITLE"] = title
                    print(f'{filename} title was {title_from_file} updated to {title}')
        except:
            print("Something went wrong trying to read the tags")
        del exiting_files[filename]
    else:
        print(f"{filename} : Processing new file")
        # if not processed it 
        try:
            with taglib.File(filepath, save_on_exit=True) as track:
                ##Key
                if 'COMMENT' in track.tags:
                    key = track.tags['COMMENT'][0] # I added all keys in the comments
                ##BPM
                if 'BPM' in track.tags:
                    file_bpm = track.tags["BPM"][0]
                    bpm = file_bpm
                    print(f"{filename} : Already had BPM ({file_bpm}) in meta data")
                else:
                    print(f"Detecting BPM on file : {filename}")
                    bpm = process_file(filepath, filename)
                    track.tags["BPM"] = f'{bpm}'
                ##Title
                if track.tags.get("TITLE") is None:
                    track.tags["TITLE"] = title
                elif title != track.tags["TITLE"][0]:
                    title_from_file = track.tags["TITLE"][0]
                    print(f"File already has Title {title_from_file} set it but it is not matching! the file name {title}!. Please Check")
                    title = title_from_file

        except:
            print("Something went wrong trying to read the tags")
        print(f'{filename} : File Procesed : {bpm} : {key}')
        print(f'-------------')
            
    csv_entry["FileName"] = filename
    csv_entry["Title"] = title
    csv_entry["BPM"] = bpm
    csv_entry["Key"] = key
    csv_entry["Path"] = filepath
    
    return csv_entry

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process .wav file to determine the Beats Per Minute.")
    parser.add_argument("--Foldername", required=True, help=".folder for processing")
    parser.add_argument(
        "--window",
        type=float,
        default=1.5,
        help="Size of the the window (seconds) that will be scanned to determine the bpm. Typically less than 10 seconds. [3]",
    )
    csv_export = []
    args = parser.parse_args()
    
    folder_path = args.Foldername
    csv_path = f'{folder_path}\\_{path.basename(folder_path)}_TracksInfo.csv'
    exiting_files = read_existiing_csv(csv_path)

    for (dirpath, dirnames, filenames) in walk(args.Foldername):
        if dirpath == folder_path:
            for filename in filenames:
                _, file_extension = path.splitext(filename)
                if file_extension == '.wav':
                    filepath = path.join(dirpath,filename)
                    csv_export.append(record_file_info(filename, filepath, exiting_files))


    with open(csv_path, 'w', encoding = global_encoding, newline='') as file: #ensure track is always on top
        writer = csv.DictWriter(file, fieldnames = csv_export[0].keys())
        writer.writeheader() 
        writer.writerows(csv_export)
        print('Update Done')