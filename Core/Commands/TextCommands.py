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
def fliptable(bot, event, *args):
    bot.send_message(event.conv, '(╯°□°）╯︵ ┻━┻')
    
@DispatcherSingleton.register
def backtable(bot, event, *args):
    bot.send_message(event.conv, '┬─┬ノ( º _ ºノ)')
    
@DispatcherSingleton.register
def lenny(bot, event, *args):
    bot.send_message(event.conv, '( ͡° ͜ʖ ͡°)')

@DispatcherSingleton.register
def navyseals(bot, event, *args):
     if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Navy Seals*
Usage: /navyseals
Purpose: Shits fury all over you.
""")
        bot.send_message_segments(event.conv, segments)
     else:
        bot.send_message(event.conv, "What the fuck did you just fucking say about me, you little bitch? I'll have you know I graduated top of my class in the Navy Seals, and I've been involved in numerous secret raids on Al-Quaeda, and I have over 300 confirmed kills. I am trained in gorilla warfare and I'm the top sniper in the entire US armed forces. You are nothing to me but just another target. I will wipe you the fuck out with precision the likes of which has never been seen before on this Earth, mark my fucking words. You think you can get away with saying that shit to me over the Internet? Think again, fucker. As we speak I am contacting my secret network of spies across the USA and your IP is being traced right now so you better prepare for the storm, maggot. The storm that wipes out the pathetic little thing you call your life. You're fucking dead, kid. I can be anywhere, anytime, and I can kill you in over seven hundred ways, and that's just with my bare hands. Not only am I extensively trained in unarmed combat, but I have access to the entire arsenal of the United States Marine Corps and I will use it to its full extent to wipe your miserable ass off the face of the continent, you little shit. If only you could have known what unholy retribution your little “clever” comment was about to bring down upon you, maybe you would have held your fucking tongue. But you couldn't, you didn't, and now you're paying the price, you goddamn idiot. I will shit fury all over you and you will drown in it. You're fucking dead, kiddo.")

@DispatcherSingleton.register
def rate(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Rate smileys*
Usage: /rate <key> 
Purpose: Send a rating smiley, key can be: agree, disagree, funny, winner, 
zing, informative, friendly, useful, optimistic, artistic, late, dumb or box.
""")
        bot.send_message_segments(event.conv, segments)
    else:
        ratings = dict(
                   agree      ="\u2714"
                  ,disagree   ="\u274c"
                  ,funny      ="\U0001f604"
                  ,winner     ="\U0001f31f"
                  ,zing       ="\u26a1"
                  ,informative="\u2139"
                  ,friendly   ="\u2764"
                  ,useful     ="\U0001f527"
                  ,optimistic ="\U0001f308"
                  ,artistic   ="\U0001f3a8"
                  ,late       ="\u23f0"
                  ,dumb       ="\U0001f4e6"
                  ,box        ="\U0001f4e6"
                  )
        try:
            bot.send_message(event.conv, ratings[args[0].lower()])
        except KeyError:
            bot.send_message(event.conv, "That's not a valid rating. You are \U0001f4e6 x 1")

@DispatcherSingleton.register
def roulette(bot, event, *args):
    #static variables
    if not hasattr(roulette, "_rouletteChamber"):
        roulette._rouletteChamber = random.randrange(0, 6)
    if not hasattr(roulette, "_rouletteBullet"):
        roulette._rouletteBullet = random.randrange(0, 6)

    if len(args) > 0 and args[0] == 'spin':
        roulette._rouletteBullet = random.randrange(0, 6)
        bot.send_message(event.conv, '*SPIN* Are you feeling lucky?')
        return
    if roulette._rouletteChamber == roulette._rouletteBullet:
        roulette._rouletteBullet = random.randrange(0, 6)
        roulette._rouletteChamber = random.randrange(0, 6)
        bot.send_message(event.conv, '*BANG*')
    else:
        bot.send_message(event.conv, '*click*')
        roulette._rouletteChamber += 1
        roulette._rouletteChamber %= 6

#TODO: move this to UtilBot or find a native replacement
def choice(iterable):
    if isinstance(iterable, (list, tuple)):
        return random.choice(iterable)
    else:
        n = 1
        m = new.module('') # Guaranteed unique value.
        ret = m
        for x in iterable:
            if random.random() < 1/n:
                ret = x
            n += 1
        if ret is m:
            raise IndexError
        return ret

def _checkTheBall(questionLength):
    if not hasattr(_checkTheBall, "_responses"):
        _checkTheBall._responses = {'positive': ['It is possible.', 'Yes!', 'Of course.',
                           'Naturally.', 'Obviously.', 'It shall be.',
                           'The outlook is good.', 'It is so.',
                           'One would be wise to think so.',
                           'The answer is certainly yes.'],
              'negative': ['In your dreams.', 'I doubt it very much.',
                           'No chance.', 'The outlook is poor.',
                           'Unlikely.', 'About as likely as pigs flying.',
                           'You\'re kidding, right?', 'NO!', 'NO.', 'No.',
                           'The answer is a resounding no.', ],
              'unknown' : ['Maybe...', 'No clue.', '_I_ don\'t know.',
                           'The outlook is hazy, please ask again later.',
                           'What are you asking me for?', 'Come again?',
                           'You know the answer better than I.',
                           'The answer is def-- oooh! shiny thing!'],
             } 
    if questionLength % 3 == 0:
        category = 'positive'
    elif questionLength % 3 == 1:
        category = 'negative'
    else:
        category = 'unknown'
    return choice(_checkTheBall._responses[category])

@DispatcherSingleton.register
def eightball(bot, event, *args):
    if len(args) > 0:
        bot.send_message(event.conv, _checkTheBall(len(' '.join(args))))
    else:
        bot.send_message(event.conv, _checkTheBall(random.randint(0, 2)))

@DispatcherSingleton.register
def fliptext(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Flip Text*
Usage: /fliptext <text>
Purpose: Flips your message 180 degrees
""")
        bot.send_message_segments(event.conv, segments)
    else:
        args = ' '.join(args)
        output = ''.join([fliptextdict.get(letter, letter) for letter in args])
        output = output[::-1]
        bot.send_message(event.conv, output)
