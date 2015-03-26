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
from .youtube_banlist import youtube_banlist

@DispatcherSingleton.register
def yt(bot, event, *args):
    youtube(bot, event, *args)
    
@DispatcherSingleton.register
def YouTube(bot, event, *args):
    youtube(bot, event, *args)

@DispatcherSingleton.register
def youtube(bot, event, *args):
    Segment = hangups.ChatMessageSegment
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*YouTube*
Usage: /youtube <optional: search parameter>
Purpose: Get the first result from YouTube\'s search using search parameter.
""")
        bot.send_message_segments(event.conv, segments)
    else:
        search_terms = " ".join(args)
        if search_terms == "" or search_terms == " ":
            search_terms = "Fabulous Secret Powers"
        query = parse.urlencode({'search_query': search_terms, 'filters': 'video'})
        results_url = 'https://www.youtube.com/results?%s' \
              % query
        headers = {
            'User-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'}
        req = request.Request(results_url, None, headers)
        resp = request.urlopen(req)
        soup = BeautifulSoup(resp)
        item_id = soup.find_all("div", class_="yt-lockup")[0]['data-context-item-id']
        query = parse.urlencode({'v': item_id})
        item_url = 'https://www.youtube.com/watch?%s' \
              % query
        item_title = soup.find_all("a", class_="yt-uix-tile-link")[0]['title']

        if item_id in youtube_banlist:
            bot.send_message(event.conv, 'Sorry, that video is banned.')
        else:
            bot.send_message_segments(event.conv, [hangups.ChatMessageSegment('Result:', is_bold=True),
                                                   hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                                                   hangups.ChatMessageSegment(item_title, hangups.SegmentType.LINK,
                                                                              link_target=item_url)])
