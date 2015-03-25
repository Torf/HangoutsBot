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

class RandomImgur:

    def __init__(self):
        # Constants
        self.config = {
            'CHARS': string.ascii_letters+string.digits, # Characters used for random URLs.
            'DIR_OUTPUT': 'output', # Output directory.
            'DEBUGS_DISPLAY': False,
            'ERRORS_DISPLAY': False, # Should all errors display?
            'IMAGE_EXTENSION': '.jpg', # Extension for search.
            'IMAGE_SIZE_MIN': 1024 * 20, # Minimum filesize for downloaded images.
            'IMAGES_DEFAULT': 25, # Number of images to download if not specified at command line.
            'IMGUR_URL_PREFIX': "http://i.imgur.com/", # Prefix for Imgur URLs.
            'THREADS': 5 # Number of threads to spawn.
        }

        # Globals
        self.queue_image_ids = queue.Queue() # Queue for random images.
        self.downloaded = 0 # Number of images downloaded.
        self.downloaded_urls = [] # images downloaded

    # Functions
    def rand_string(self, string_length):
        return ''.join([random.choice(self.config['CHARS']) for x in range(string_length)])

    def path_get(self):
        if sys.platform.startswith('win32'):
            path = os.getcwd()+'\\'+self.config['DIR_OUTPUT']+'\\'
        else:
            path = os.getcwd()+'/'+self.config['DIR_OUTPUT']+'/'
        return path

    def path_create(self):
        path = self.path_get()
        if not os.path.exists(path):
            os.makedirs(path)

    def error_print(self, error):
        if self.config['ERRORS_DISPLAY']:
            print(error)
    
    def debug_print(self, info):
        if self.config['DEBUGS_DISPLAY']:
            print(info)

    # Thread
    class ThreadSpawn(threading.Thread):

        def __init__(self, queue, lock, parent):
            threading.Thread.__init__(self)
            self.queue = queue
            self.lock = lock
            self.parent = parent

        def get_images(self, num_pics):
            path = self.parent.path_get()
            for i in range(num_pics):
                success = False
                while not success:
                    image_name = self.parent.rand_string(5) + self.parent.config['IMAGE_EXTENSION']
                    url = self.parent.config['IMGUR_URL_PREFIX']+image_name
                    req = Request(url)
                    data = None

                    try:
                        data = urlopen(req)
                    except HTTPError as e:
                        self.parent.error_print("HTTP Error: "+str(e.code)+' '+image_name)
                    except URLError as e:
                        self.parent.error_print("URL Error: "+str(e.reason)+' '+image_name)

                    if data:
                        try:
                            data = data.read();

                            # Check if placeholder image.
                            if 'd835884373f4d6c8f24742ceabe74946' == hashlib.md5(data).hexdigest():
                                self.parent.error_print("Received placeholder image: "+image_name)
                            # Check if image is above minimum size.
                            elif self.parent.config['IMAGE_SIZE_MIN'] > sys.getsizeof(data):
                                self.parent.error_print("Received image is below minimum size threshold: "+image_name)
                            # Write image to disk.
                            else:
                                success = True
                                self.local_file = open(path+image_name, "wb")
                                self.local_file.write(data)
                                self.local_file.close()
                                self.lock.acquire()
                                self.parent.downloaded = self.parent.downloaded + 1
                                self.parent.downloaded_urls.append(image_name)
                                self.lock.release()
                                self.parent.debug_print("Downloaded image #"+str(self.parent.downloaded)+": "+image_name)

                            del data
                        except Exception as e:
                            self.parent.error_print("Download failed: "+image_name+ " (%s)" % e)

        def run(self):
            while True:
                # Grabs num from queue - note that num is arbitrary and isn't used.
                num = self.queue.get()

                # Grabs a pic.
                self.get_images(1)

                # Signals to queue job is done.
                self.queue.task_done()

    # Main
    def generate(self, image_limit):
        time_start = time.time()
        
        self.downloaded = 0
        self.downloaded_urls = []

        self.path_create()
        self.debug_print('Output folder is: "'+self.path_get()+'"')

        # Image limit.
        self.debug_print('Retreiving '+str(image_limit)+' random images.')

        # Populate queue with data.
        for n in range(image_limit):
            self.queue_image_ids.put(n)
   
        # Create shared lock.
        lock = Lock()
   
        # Spawn a pool of threads, and pass them queue instance.
        self.debug_print("Spawning "+str(self.config['THREADS'])+" threads.\n")
        for i in range(self.config['THREADS']):
            t = RandomImgur.ThreadSpawn(self.queue_image_ids, lock, self)
            t.daemon = True
            t.start()

        # Wait on the queue until everything has been processed.
        self.queue_image_ids.join()

        # Completion.
        time_end = time.time()
        time_total = round(time_end - time_start, 2)
        rate = round(time_total / image_limit, 2)
        self.debug_print("\n")
        self.debug_print('Completed in: '+str(time_total)+' seconds.')
        self.debug_print("Approximately "+str(rate)+' seconds per image.')

        return self.downloaded_urls
