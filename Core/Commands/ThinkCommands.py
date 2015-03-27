import json
from urllib import parse
from urllib import request
import re
import html
import os
import string
import unicodedata
import sys
import time

from bs4 import BeautifulSoup
import hangups
from hangups.ui.utils import get_conv_name

from Libraries.cleverbot import ChatterBotFactory, ChatterBotType
from Core.Commands.Dispatcher import DispatcherSingleton
from Core.Util import UtilBot

punc_tbl = dict.fromkeys(i for i in range(sys.maxunicode)
                      if unicodedata.category(chr(i)).startswith('P'))
banned_word_regex = re.compile('Cleverbot', re.IGNORECASE)
last_answer = {}

@DispatcherSingleton.register_hidden
def think(bot, event, *args):
    if bot.chatterbot and len(args) > 0:
        inputmsg = ' '.join(args)
        
        if wasSpeakingToBot(bot, event):
            yield from sendAnswer(bot, event, inputmsg)
        
        elif isSpeakingToBot(bot, inputmsg, *args):
            yield from sendAnswer(bot, event, inputmsg)


def wasSpeakingToBot(bot, event):
    if event.user_id.gaia_id in last_answer and last_answer[event.user_id.gaia_id]:
        diff = event.timestamp - last_answer[event.user_id.gaia_id]
        
        if diff.total_seconds() >= 0 and diff.total_seconds() <= bot.config['autoreplies_maxtime']:
            return True
        else:
            del last_answer[event.user_id.gaia_id]
    
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
        
    cleanmsg = remove_punctuation(cleanmsg).strip()
    if cleanmsg.endswith(botName):
        return True
    
    return False


def sendAnswer(bot, event, inputmsg, attempts=2):
    yield from bot.send_typing(event.conv)
    try:
        answer = bot.chatterbot.think(inputmsg)
    except Exception:
        print('Cleverbot error : waiting until next attempt (%s attempts left)'%attempts)
        time.sleep(10)
        if attempts > 0:
            yield from sendAnswer(bot, event, inputmsg, attempts - 1)
        return
    last_answer[event.user_id.gaia_id] = event.timestamp
    yield from bot.send_message(event.conv, filter_banned_word(bot, answer))

@DispatcherSingleton.register_hidden
def taggle(bot, event, *args):
    stopthink(bot, event, *args)

@DispatcherSingleton.register_hidden
def stopthink(bot, event, *args):
    if bot.chatterbot:
        if event.user_id.gaia_id in last_answer:
            del last_answer[event.user_id.gaia_id]

def remove_punctuation(text):
    return text.translate(punc_tbl)

def filter_banned_word(bot, text):
    return banned_word_regex.sub(bot.config['autoreplies_name'], text)
