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
from .fliptextdict import fliptextdict

@DispatcherSingleton.register
def latex(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*LaTeX*
Usage: /latex <LaTeX code>
Purpose: Renders LaTeX code to an image and sends it
""")
        yield from bot.send_message_segments(event.conv, segments)
    else:
        cmd = "texvc /tmp images '" + \
              ' '.join(args).replace("'", "'\\''") + \
              "' utf-8 'rgb 1.0 1.0 1.0'"
        print('args: ')
        print(cmd)
        output = subprocess.check_output(cmd, shell=True)
        output = output.decode(encoding='UTF-8')
        print(output)
        filename = output[1:33] + '.png'
        filename = os.path.join('images', filename)
        imageID = yield from bot._client.upload_image(filename)
        bot.send_image(event.conv, imageID)

@DispatcherSingleton.register
def greentext(bot, event, *args):
    """
    *Greentext*
    Usage: /greentext <text>
    Purpose: makes your text green and adds an epic maymay arrow
    """
    filename = 'greentext.png'
    message = ' '.join(args)
    if message[0] == '>':
        message = message[1:]
    message = message.replace('>', '\n>')
    message = '>' + message
    print(message)
    cmd = ['convert',
           '-size',
           '164x',
           '-font',
           '/usr/share/fonts/truetype/windows/arial.ttf',
           '-pointsize',
           '13',
           '-fill',
           '#789922',
           '-background',
           '#ffffee',
           'caption:%s' % message,
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
