import asyncio
from datetime import timedelta, datetime
from fractions import Fraction
import glob
import json
import os
import random
import threading
from urllib import parse, request
from bs4 import BeautifulSoup
from dateutil import parser
import hangups
import re
import requests
from Core.Commands.Dispatcher import DispatcherSingleton
from Core.Util import UtilBot
from Libraries import Genius
from Libraries.random_imgur import RandomImgur
import errno
from glob import glob
import subprocess

@DispatcherSingleton.register
def image(bot, event, *args):
    yield from img(bot, event, *args)

@DispatcherSingleton.register
def img(bot, event, *args):
    if len(args) > 0:
        yield from bot.send_typing(event.conv)
        url = args[0]
        file_exception = False
        try:
            imageids_filename = os.path.join('images', 'imageids.json')
            imageids = json.loads(open(imageids_filename, encoding='utf-8').read(), encoding='utf-8')
            imageID = imageids.get(url)
        except IOError as e:
            if e.errno == errno.ENOENT:
                imageids = {}
            else:
               print('Exception:')
               print(str(e))
               file_exception = True
            imageID = None;
        if imageID is None:
            filename = UtilBot.download_image(url, 'images')
            imageID = yield from bot._client.upload_image(filename)
            if not file_exception:
                imageids[url] = imageID
                with open(imageids_filename, 'w') as f:
                    json.dump(imageids, f, indent=2, sort_keys=True)
                os.remove(filename)
        bot.send_image(event.conv, imageID)

@DispatcherSingleton.register
def imgur(bot, event, *args):
    yield from bot.send_typing(event.conv)
    # get random imgur image
    randImgur = RandomImgur()
    filename = randImgur.generate(1)[0]
    filepath = 'output/'+filename
    link_url = 'http://i.imgur.com/'+filename
    # upload it
    imageID = yield from bot._client.upload_image(filepath)
    os.remove(filepath)
    # send it
    bot.send_image(event.conv, imageID)
    yield from bot.send_message_segments(event.conv, [hangups.ChatMessageSegment(link_url, hangups.SegmentType.LINK, link_target=link_url)])
    
    
@DispatcherSingleton.register
def colour(bot, event, *args):
    yield from color(bot, event, *args)
 
@DispatcherSingleton.register
def color(bot, event, *args):
    yield from bot.send_typing(event.conv)
    filename = 'color.png'
    cmd = ['convert',
           '-size',
           '500x500',
           'xc:%s' % ' '.join(args),
           filename]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        output = output.decode(encoding='UTF-8')
        if output != '':
            print(output)
        imageID = yield from bot._client.upload_image(filename)
        bot.send_image(event.conv, imageID)
        os.remove(filename)
    except subprocess.CalledProcessError as e:
        output = e.output.decode(encoding='UTF-8')
        if output != '':
            print(output)
