import json
from urllib import parse
from urllib import request
import re
import html
import os

from bs4 import BeautifulSoup
import hangups
from hangups.ui.utils import get_conv_name

from Libraries.cleverbot import ChatterBotFactory, ChatterBotType
from Core.Commands.Dispatcher import DispatcherSingleton
from Core.Util import UtilBot

last_answer = {}

@DispatcherSingleton.register_hidden
def think(bot, event, *args):
    if bot.chatterbot:
        inputmsg = ' '.join(args)
        answer = bot.chatterbot.think(inputmsg)
        
        last_answer[event.user_id] = event.timestamp
        yield from bot.send_message(event.conv, answer)
        
@DispatcherSingleton.register_hidden
def cleanthink(bot, event, *args):
    if bot.chatterbot:
        cleanargs = []
        for arg in args:
            if arg.lower() != bot.config['autoreplies_name']:
                cleanargs.append(arg)
        
        yield from think(bot, event, *cleanargs)
        
@DispatcherSingleton.register_hidden
def continuethink(bot, event, *args):
    if bot.chatterbot:
        if event.user_id in last_answer:
            if last_answer[event.user_id] == event.timestamp:
                for arg in args:
                    if arg.lower() == bot.config['autoreplies_name']:
                        return #already handled, TODO: enhance it
            
            diff = last_answer[event.user_id] - event.timestamp
            if diff.total_seconds() < 120:
                yield from think(bot, event, *args)

@DispatcherSingleton.register_hidden
def stopthink(bot, event, *args):
    if bot.chatterbot:
        if event.user_id in last_answer:
            del last_answer[event.user_id]
