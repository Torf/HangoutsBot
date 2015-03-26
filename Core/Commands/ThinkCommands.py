import json
from urllib import parse
from urllib import request
import re
import html
import os
import string
import unicodedata
import sys

from bs4 import BeautifulSoup
import hangups
from hangups.ui.utils import get_conv_name

from Libraries.cleverbot import ChatterBotFactory, ChatterBotType
from Core.Commands.Dispatcher import DispatcherSingleton
from Core.Util import UtilBot

punc_tbl = dict.fromkeys(i for i in range(sys.maxunicode)
                      if unicodedata.category(chr(i)).startswith('P'))
last_answer = {}

@DispatcherSingleton.register_hidden
def think(bot, event, *args):
    if bot.chatterbot and len(args) > 0:
        inputmsg = ' '.join(args)
        print('inputmsg:%s'%inputmsg)
        if wasSpeakingToBot(event):
            yield from sendAnswer(bot, event, inputmsg)
        
        elif isSpeakingToBot(bot, inputmsg, *args):
            yield from sendAnswer(bot, event, inputmsg)


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
    print('botName:%s  -  firstWord:%s'%(botName, firstWord))
    # @someone blabla
    if firstWord.startswith('@'): 
        if firstWord.startswith('@'+botName):
            args[0] = args[0][len('@'+botName):]
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
    print('cleanmsg:%s'%cleanmsg)
    cleanmsg = remove_punctuation(cleanmsg).strip()
    if cleanmsg.endswith(botName):
        return True
    print('cleanmsg:%s'%cleanmsg)
    return False


def sendAnswer(bot, event, inputmsg):
    yield from bot.send_typing(event.conv)
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

def remove_punctuation(text):
    return text.translate(punc_tbl)
