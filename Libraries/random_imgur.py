import argparse
import hashlib
from multiprocessing import Lock
import os
import queue
import random
import string
import sys
import threading
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

# From https://github.com/ParhelicMedia/random-imgur © 2015 All Rights Reserved

# Constants
CHARS = string.ascii_letters+string.digits # Characters used for random URLs.
DIR_OUTPUT = 'output' # Output directory.
ERRORS_DISPLAY = True # Should all errors display?
IMAGE_EXTENSION = ".jpg" # Extension for search.
IMAGE_SIZE_MIN = 1024 * 20 # Minimum filesize for downloaded images.
IMAGES_DEFAULT = 25 # Number of images to download if not specified at command line.
IMGUR_URL_PREFIX = "http://i.imgur.com/" # Prefix for Imgur URLs.
THREADS = 5 # Number of threads to spawn.

# Globals
queue_image_ids = queue.Queue() # Queue for random images.
downloaded_images = [] # images downloaded.

# Functions
def rand_string(string_length):
    return ''.join([random.choice(CHARS) for x in range(string_length)])

def path_get():
    if sys.platform.startswith('win32'):
        path = os.getcwd()+'\\'+DIR_OUTPUT+'\\'
    else:
        path = os.getcwd()+'/'+DIR_OUTPUT+'/'
    return path

def path_create():
    path = path_get()
    if not os.path.exists(path):
        os.makedirs(path)

# Thread
class ThreadSpawn(threading.Thread):

    def __init__(self, queue, lock):
          threading.Thread.__init__(self)
          self.queue = queue
          self.lock = lock

    def get_images(self, num_pics):
        path = path_get()
        for i in range(num_pics):
            success = False
            while not success:
                image_name = rand_string(5) + IMAGE_EXTENSION
                url = IMGUR_URL_PREFIX+image_name
                req = Request(url)
                data = None

                try:
                    data = urlopen(req)
                except HTTPError as e:
                    #print("HTTP Error: "+str(e.code)+' '+image_name)
                except URLError as e:
                    #print("URL Error: "+str(e.reason)+' '+image_name)

                if data:
                    try:
                        data = data.read();

                        # Check if placeholder image.
                        if 'd835884373f4d6c8f24742ceabe74946' == hashlib.md5(data).hexdigest():
                            #error_print("Received placeholder image: "+image_name)
                        # Check if image is above minimum size.
                        elif IMAGE_SIZE_MIN > sys.getsizeof(data):
                            #error_print("Received image is below minimum size threshold: "+image_name)
                        # Write image to disk.
                        else:
                            success = True
                            self.local_file = open(path+image_name, "wb")
                            self.local_file.write(data)
                            self.local_file.close()
                            lock.acquire()
                            global downloaded_images
                            downloaded_images.append(image_name)
                            lock.release()

                        del data
                    except:
                        #print("Download failed: "+image_name)

    def run(self):
        while True:
            # Grabs num from queue - note that num is arbitrary and isn't used.
            num = self.queue.get()

            # Grabs a pic.
            self.get_images(1)

            # Signals to queue job is done.
            self.queue.task_done()

# Main
def generate_imgur(count)
    time_start = time.time()
    downloaded_images = []

    # Image path.
    path_create()
    #print('Output folder is: "'+path_get()+'"')

    # Image limit.
    image_limit = count
    #print('Retreiving '+str(image_limit)+' random images.')

    # Populate queue with data.
    for n in range(image_limit):
        queue_image_ids.put(n)
   
    # Create shared lock.
    lock = Lock()
   
    # Spawn a pool of threads, and pass them queue instance.
    #print("Spawning "+str(5)+" threads.\n")
    for i in range(THREADS):
        t = ThreadSpawn(queue_image_ids, lock)
        t.daemon = True
        t.start()

    # Wait on the queue until everything has been processed.
    queue_image_ids.join()

    # Completion.
    time_end = time.time()
    time_total = round(time_end - time_start, 2)
    rate = round(time_total / image_limit, 2)
    return downloaded_images;
