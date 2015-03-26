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
transtable = string.maketrans("","")

@DispatcherSingleton.register_hidden
def think(bot, event, *args):
    if bot.chatterbot and len(args) > 0:
        inputmsg = ' '.join(args)
        
        if wasSpeakingToBot(event):
            answer(bot, event, inputmsg)
        
        elif isSpeakingToBot(bot, inputmsg, *args):
            answer(bot, event, inputmsg)


def wasSpeakingToBot(event):
    if event.user_id in last_answer and last_answer[event.user_id]:
        diff = last_answer[event.user_id] - event.timestamp
        if diff.total_seconds() >= 0 and diff.total_seconds() <= 480:
            return True
        else:
            del last_answer[event.user_id]
    
    return False


def isSpeakingToBot(bot, inputmsg, *args):
    botName = bot.config['autoreplies_name'].lower()
    firstWord = args[0].lower()
    
    # @someone blabla
    if firstWord.startswith('@'): 
        if firstWord.startswith('@'+botName):
            return True
        else:
            return False
            
    # Someone, blabla
    if firstWord.startswith(botName):
        return True
    
    # blabla Someone!
    cleanmsg = inputmsg.lower()
    if botName not in cleanmsg:
        return False
    
    cleanmsg = cleanmsg.translate(transtable, string.punctuation).strip()
    if cleanmsg.endswith(botName):
        return True
    
    return False


def answer(bot, event, inputmsg):
    answer = bot.chatterbot.think(inputmsg)
    last_answer[event.user_id] = event.timestamp
    yield from bot.send_message(event.conv, answer)

@DispatcherSingleton.register_hidden
def taggle(bot, event, *args):
    stopthink(bot, event, *args)

@DispatcherSingleton.register_hidden
def stopthink(bot, event, *args):
    if bot.chatterbot:
        if event.user_id in last_answer:
            del last_answer[event.user_id]
