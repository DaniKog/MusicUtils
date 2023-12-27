# coding: utf-8-sig
global_encoding = 'utf-8-sig'
import argparse
import csv
import shutil
import os
from tempfile import NamedTemporaryFile

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process .wav file to determine the Beats Per Minute.")
    parser.add_argument("--Folderpath", required=True, help=".folder for processing")
    csv_export = []
    args = parser.parse_args()
    
    folder_path = args.Folderpath
    csv_name = f'_{os.path.basename(folder_path)}_TracksInfo.csv'
    csv_path = f'{folder_path}\\{csv_name}'
    if os.path.isfile(csv_path) == False:
        print(f"csv {csv_path} does not exist")

    tempfile = NamedTemporaryFile(mode='w', delete=False, newline='', encoding = global_encoding)
    if os.path.isfile(csv_path):
        with open(csv_path, encoding = global_encoding) as csvfile, tempfile:
            reader = csv.DictReader(csvfile)
            writer = csv.DictWriter(tempfile, fieldnames = reader.fieldnames)
            writer.writeheader()
            for row in reader:
                old_filename = row['FileName']
                title = row['Title']
                key = row['Key']
                BPM = row['BPM']
                new_filename = f'{key}.{BPM}. {title}.wav'
                if old_filename != new_filename:
                    oldpath = row['Path']
                    if os.path.isfile(oldpath):
                        newpath = os.path.join(folder_path,f'{new_filename}')
                        os.rename(oldpath, newpath)
                        row['FileName'] = new_filename
                        row['Path'] = newpath
                        print(f'Renamed: {old_filename}')
                        print(f'To: {new_filename}')
                        print(f'--------------')
                    else:
                        print(f'ERROR: Path does not exist! {oldpath}')
                writer.writerow(row)
    else:
        print(f'{csv_path} does not exist')
    shutil.move(tempfile.name, csv_path)
    print("Done")