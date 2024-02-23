#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import select
import sys
import subprocess
import random
import time
import traceback
import datetime


def list_files(folder, exclude_dirs={"@eaDir", ".picasaoriginals", "#recycle"}, exclude_dir_ext={".photoslibrary"}):
    """The function enumerates the given folder and returns a 
    list of full paths of the files in the folder recursively.
    
    @return: A shuffled list of full paths of the files in the folder.
    """

    # if folder is a file, then return the file path
    if os.path.isfile(folder):
        return [folder]

    file_list = []
    
    for root, dirs, files in os.walk(folder, topdown=True):
        # remove exclude_dirs from dirs
        names_to_remove = []
        for name in dirs:
            if name in exclude_dirs:
                names_to_remove.append(name)
            elif os.path.splitext(name)[1].lower() in exclude_dir_ext:
                names_to_remove.append(name)

        for name in names_to_remove:
            dirs.remove(name)

        for file in files:
            file_list.append(os.path.join(root, file))

    # permute the file list in random order, to allow the user detect if all photos have been previously imported.
    random.shuffle(file_list)
    return file_list

def get_file_extension(file_list):
    """The function returns the unique set of file extentions from a list of full paths."""
    ext_list = set()
    for file in file_list:
        ext_list.add(os.path.splitext(file)[1])
    return ext_list

def filter_by_file_extention(file_list, ext_list):
    """The function filters the file list based on the given list of file extensions. The filtering is case insensitive.""" 
    filtered_list = []
    normalized_ext_list = {ext.lower() for ext in ext_list}
    for file in file_list:
        if os.path.splitext(file)[1].lower() in normalized_ext_list:
            filtered_list.append(file)
    return filtered_list

def filter_imported_photos(file_list):
    """The function filters the file list based on the given list of imported photos."""
    # load the imported photos from the "imported_photos.csv" file
    imported_list = []
    try:
        with open("imported_photos.csv", "r") as f:
            imported_list = f.readlines()
            imported_list = {file.rstrip() for file in imported_list}
    except FileNotFoundError:
        pass

    filtered_list = []
    for file in file_list:
        if file not in imported_list:
            filtered_list.append(file)

    return filtered_list

def filter_error_importing(file_list):
    """The function filters the file list based on the given list of error importing photos."""
    # load the error importing photos from the "error_importing.csv" file
    error_list = []
    try:
        with open("error_importing.csv", "r") as f:
            error_list = f.readlines()
            error_list = {file.rstrip() for file in error_list}
    except FileNotFoundError:
        pass

    filtered_list = []
    for file in file_list:
        if file not in error_list:
            filtered_list.append(file)
    return filtered_list



def send_imessage(message):
    apple_id = os.environ.get('APPLE_ID')
    applescript = f'''
    tell application "Messages"
        send "{message}" to buddy "{apple_id}" of (service 1 whose service type is iMessage)
    end tell
    '''
    subprocess.run(['osascript', '-e', applescript])

def wait_for_space(min_disk_space):
    """The function waits until there are enough space in the disk."""
    stat = os.statvfs(os.path.expanduser("~/"))
    free_space = stat.f_bavail * stat.f_frsize
    if free_space < min_disk_space:
        print() # add a new line
        # Send an imessage to the user
        send_imessage("Not enough space in your storage. Photos importing will retry every 5 minutes.")
        # wait until there are more than enough space in the disk
        while free_space < min_disk_space * 1.1:
            print(f"\rNot enough space in your storage. Will retry in 5 minutes (or press ENTER):", end="")
            # wait for the user to type any key or 5 minutes
            i, o, e = select.select([sys.stdin], [], [], 300)
            if i:
                input()
            stat = os.statvfs(os.path.expanduser("~/"))
            free_space = stat.f_bavail * stat.f_frsize
        send_imessage("Photos importing resumes now.")


def import_photos(file_list, batch_size=500, min_disk_space=15*1024*1024*1024):
    """The function imports the given list of photos to the Photos app.
    
    @param file_list: The list of full paths of the photos to import.
    @param batch_size: The number of photos to import before restarting the Photos app.
    @param min_disk_space: The minimum disk space in bytes to wait before importing the next photo.
    @param timeout: The maximum time in seconds to wait for the import process to finish.

    The function **append** the list of imported photos to the "imported_photos.csv" file and the 
    list of error importing photos to the "error_importing.csv" file.
    """
    
    average_time = 1 # seconds per file
    count=0
    error_count=0
    dup_count=0
    max_print_width = 1 # The 0 width format is now allowed in f-string.

    # open the "imported_photos.csv" file in write mode
    with open("imported_photos.csv", "a") as f, open("error_importing.csv", "a") as e:

        for file in file_list:
            # test if the file still exists as this is a long process
            if not os.path.exists(file):
                print(f"\n  Files no longer exit or have been moved.")
                send_imessage(f"Files no longer exit or have been moved.")
                # we need to quit the processing because osxphotos will not report an error if the file is not found
                break

            # wait for the disk space to be available   
            wait_for_space(min_disk_space)
            begin = time.time()
            # run the CLI command to import photos into the Photos app, and get the stdout and stderr as a tuple
            try:
                command = f'osxphotos import --album "{{filepath.parent.name}}"  --verbose --skip-dups --dup-albums --sidecar --keyword "{{person}}" "{file}" 2>&1'
                process = subprocess.Popen(command, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE,  text=True, shell=True)
                # Wait for the process to finish and get the stdout and exit code
                # set timeout in proportion to the file size
                timeout = max(30, 10 * os.path.getsize(file) // 1024 // 1024)
                stdout, stderr = process.communicate(timeout=timeout) 
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                # The import process can be blocked when the Photos app is not responding or asking for confirmation.
                print(f"\n  Terminating importing after no responses for {timeout} secs.")
                if os.system("pgrep osxphotos > /dev/null 2>&1") == 0:
                    os.system("killall osxphotos > /dev/null 2>&1")         
                exit_code = -1

            count += 1
            if exit_code != 0:
                e.write(f"{file}\n")
                e.flush()
                error_count += 1
            else:
                if "Skipping duplicate" in stdout:
                    dup_count += 1

                f.write(f"{file}\n")
                f.flush()

            # kills the Photos app after timeoutprocessing batch_size of photos
            # or when the import process timeout 
            if exit_code == -1 or count % batch_size == 0:
                if os.system("pgrep Photos > /dev/null 2>&1") == 0:
                    progress = f"  Restarting the Photos app..."
                    print(f"\r{progress:{max_print_width}}", end="")
                    time.sleep(5) # to ensure the Photos app has saved all the changes
                    if os.system("pgrep Photos > /dev/null 2>&1") == 0:
                        os.system("killall Photos > /dev/null 2>&1")
            
            # Show remaining time and the progress
            average_time = average_time * 0.8 + (time.time() - begin) * 0.2
            time_remaining = (len(file_list) - count) * average_time // 60 * 60
            precentage_remaining = (len(file_list) - count) * 100 // len(file_list)
            progress = f"  {precentage_remaining}% or {datetime.timedelta(seconds=time_remaining)} remaining ({count} processed, {error_count} errors and {dup_count} duplicates)."
            max_print_width = max(max_print_width, len(progress))
            print(f"\r{progress:{max_print_width}}", end="")

        progress = f"  {count} processed, {error_count} errors and {dup_count} duplicates."
        print(f"\r{progress:{max_print_width}}")

    
def show_usage():
    print("\nUsage: APPLE_ID=your_apple_id@icloud.com python3 apple-photos-import.py <folder>")
    print("  <folder> - The folder path to import the photos from.")
    print("  <your_apple_id@icloud.com> - The apple ID to receive notificadtions.")
    print("Example: APPLE_ID=your_apple_id@icloud.com python3 apple-photos-import.py ~/Downloads/Photos")

if __name__ == "__main__":
    # check if the osxphotos is installed
    if os.system("osxphotos --version > /dev/null 2>&1")!= 0:
        print("Please install osxphotos by running 'pip3 install osxphotos'")
        show_usage()
        sys.exit(1)

    # check if the environment variable APPLE_ID is set
    if os.environ.get('APPLE_ID') is None:
        print("Please set the environment variable APPLE_ID with your Apple ID to receive notificaditons.")
        show_usage()
        sys.exit(1)

    # check if the folder is provided
    if len(sys.argv) < 2:
        print("Please provide the folder path as the first argument.")
        show_usage()
        sys.exit(1)

    # check if the folder exists
    folder = sys.argv[1]
    if not os.path.exists(folder):
        print(f"The folder {folder} does not exist.")
        show_usage()
        sys.exit(1)

    # list all the files in the folder
    print(f"Scanning files in {folder} ...")
    file_list = list_files(folder)
    print(f"{len(file_list)} files found.")

    # get the unique set of file extensions
    ext_set = get_file_extension(file_list)
    ext_set = {ext.lower() for ext in ext_set}
    supported_ext = {'.jpeg', '.ARW', '.jpg', '.png', '.HEIC', '.mp4', '.mov', '.PNG', '.MOV', '.JPG', ".nef", ".gif", ".mpg", ".m4v", ".tif", ".tiff", ".heif", ".heic", ".avif", ".webp", ".avi", ".bmp", ".wmv"}
    supported_ext = {ext.lower() for ext in supported_ext}
    print(f"Ignoring file extentions (case insensitive): {list(ext_set - supported_ext)}")

    # filter the file list based on the given list of file extensions
    file_list = filter_by_file_extention(file_list, supported_ext)
    num_supported_photos = len(file_list)
    print(f"{num_supported_photos} photos found in supported formats.")

    # Remove previously imported photos and those with errors
    
    file_list = filter_imported_photos(file_list)
    num_imported_photos = num_supported_photos - len(file_list)
    print(f"{num_imported_photos} photos were previously imported.")

    file_list = filter_error_importing(file_list)
    num_failed_photos = num_supported_photos - len(file_list) - num_imported_photos
    print(f"{num_failed_photos} photos were priviously tried but failed.")

    # we send a message to the user at this point to make sure we are granted the proper permission to send messages
    msg = f"Importing {len(file_list)} photos into the Photos app."
    print(msg)
    send_imessage(msg)

    # importing the photos
    import_photos(file_list)
    print("Done.")
    sys.exit(0)
