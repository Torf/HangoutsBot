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
import errno
from glob import glob
import subprocess
from .fliptextdict import fliptextdict
from .youtube_banlist import youtube_banlist

reminders = []

@DispatcherSingleton.register
def me(bot, event, *args):
    pass

@DispatcherSingleton.register
def image(bot, event, *args):
    yield from img(bot, event, *args)

@DispatcherSingleton.register
def img(bot, event, *args):
    if len(args) > 0:
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
def count(bot, event, *args):
    words = ' '.join(args)
    count = UtilBot.syllable_count(words)
    bot.send_message(event.conv,
                     '"' + words + '"' + " has " + str(count) + (' syllable.' if count == 1 else ' syllables.'))

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
def udefine(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Urbanly Define*
Usage: /udefine <word to search for> \
<optional: definition number [defaults to 1st]>
Purpose: Define a word.
""")
        bot.send_message_segments(event.conv, segments)
    else:
        api_host = 'http://urbanscraper.herokuapp.com/search/'
        num_requested = 0
        returnall = False
        if len(args) == 0:
            bot.send_message(event.conv, "Invalid usage of /udefine.")
            return
        else:
            if args[-1] == '*':
                args = args[:-1]
                returnall = True
            if args[-1].isdigit():
                # we subtract one here because def #1 is the 0 item in the list
                num_requested = int(args[-1]) - 1
                args = args[:-1]

            term = parse.quote('.'.join(args))
            response = requests.get(api_host + term)
            error_response = 'No definition found for \"{}\".'.format(' '.join(args))
            if response.status_code != 200:
                bot.send_message(event.conv, error_response)
            result = response.content.decode()
            result_list = json.loads(result)
            num_requested = min(num_requested, len(result_list) - 1)
            num_requested = max(0, num_requested)
            result = result_list[num_requested].get(
                'definition', error_response)
            if returnall:
                segments = []
                for string in result_list:
                    segments.append(hangups.ChatMessageSegment(string))
                    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                bot.send_message_segments(event.conv, segments)
            else:
                segments = [hangups.ChatMessageSegment(' '.join(args), is_bold=True),
                            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                            hangups.ChatMessageSegment(result + ' [{0} of {1}]'.format(
                                num_requested + 1, len(result_list)))]
                bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def remind(bot, event, *args):
    # TODO Implement a private chat feature. Have reminders save across reboots?
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Remind*
Usage: /remind <optional: date [defaults to today]> \
<optional: time [defaults to an hour from now]> Message
Usage: /remind
Usage: /remind delete <index to delete>
Purpose: Will post a message the date and time specified to \
the current chat. With no arguments, it'll list all the reminders.
""")
        bot.send_message_segments(event.conv, segments)
    else:
        if len(args) == 0:
            segments = [hangups.ChatMessageSegment('Reminders:', is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            if len(reminders) > 0:
                for x in range(0, len(reminders)):
                    reminder = reminders[x]
                    reminder_timer = reminder[0]
                    reminder_text = reminder[1]
                    date_to_post = datetime.now() + timedelta(seconds=reminder_timer.interval)
                    segments.append(
                        hangups.ChatMessageSegment(
                            str(x + 1) + ' - ' + date_to_post.strftime('%m/%d/%y %I:%M%p') + ' : ' + reminder_text))
                    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.pop()
                bot.send_message_segments(event.conv, segments)
            else:
                bot.send_message(event.conv, "No reminders are currently set.")
            return
        if args[0] == 'delete':
            try:
                x = int(args[1])
                x -= 1
            except ValueError:
                bot.send_message(event.conv, 'Invalid integer: ' + args[1])
                return
            if x in range(0, len(reminders)):
                reminder_to_remove_text = reminders[x][1]
                reminders[x][0].cancel()
                reminders.remove(reminders[x])
                bot.send_message(event.conv, 'Removed reminder: ' + reminder_to_remove_text)
            else:
                bot.send_message(event.conv, 'Invalid integer: ' + str(x + 1))
            return

        def send_reminder(bot, conv, reminder_time, reminder_text, loop):
            asyncio.set_event_loop(loop)
            bot.send_message(conv, reminder_text)
            for reminder in reminders:
                if reminder[0].interval == reminder_time and reminder[1] == reminder_text:
                    reminders.remove(reminder)

        args = list(args)
        date = str(datetime.now().today().date())
        time = str((datetime.now() + timedelta(hours=1)).time())
        set_date = False
        set_time = False
        index = 0
        while index < len(args):
            item = args[index]
            if item[0].isnumeric():
                if '/' in item or '-' in item:
                    date = item
                    args.remove(date)
                    set_date = True
                    index -= 1
                else:
                    time = item
                    args.remove(time)
                    set_time = True
                    index -= 1
            if set_date and set_time:
                break
            index += 1

        reminder_time = date + ' ' + time
        if len(args) > 0:
            reminder_text = ' '.join(args)
        else:
            bot.send_message(event.conv, 'No reminder text set.')
            return
        current_time = datetime.now()
        try:
            reminder_time = parser.parse(reminder_time)
        except (ValueError, TypeError):
            bot.send_message(event.conv, "Couldn't parse " + reminder_time + " as a valid date.")
            return
        if reminder_time < current_time:
            reminder_time = current_time + timedelta(hours=1)
        reminder_interval = (reminder_time - current_time).seconds
        reminder_timer = threading.Timer(reminder_interval, send_reminder,
                                         [bot, event.conv, reminder_interval, reminder_text, asyncio.get_event_loop()])
        reminders.append((reminder_timer, reminder_text))
        reminder_timer.start()
        bot.send_message(event.conv, "Reminder set for " + reminder_time.strftime('%B %d, %Y %I:%M%p'))


@DispatcherSingleton.register
def finish(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Finish*
Usage: /finish <lyrics to finish> <optional: * symbol to show guessed song>
Purpose: Finish a lyric!
""")
        bot.send_message_segments(event.conv, segments)
    else:
        showguess = False
        if args[-1] == '*':
            showguess = True
            args = args[0:-1]
        lyric = ' '.join(args)
        songs = Genius.search_songs(lyric)

        if len(songs) < 1:
            bot.send_message(event.conv, "I couldn't find your lyrics.")
        if songs[0].artist.name == 'James Joyce':
            bot.send_message(event.conv, "Sorry, that author is banned.")
            return
        lyrics = songs[0].raw_lyrics
        anchors = {}

        lyrics = lyrics.split('\n')
        currmin = (0, UtilBot.levenshtein_distance(lyrics[0], lyric)[0])
        for x in range(1, len(lyrics) - 1):
            try:
                currlyric = lyrics[x]
                if not currlyric.isspace():
                    # Returns the distance and whether or not the lyric had to be chopped to compare
                    result = UtilBot.levenshtein_distance(currlyric, lyric)
                else:
                    continue
                distance = abs(result[0])
                lyrics[x] = lyrics[x], result[1]

                if currmin[1] > distance:
                    currmin = (x, distance)
                if currlyric.startswith('[') and currlyric not in anchors:
                    next = UtilBot.find_next_non_blank(lyrics, x)
                    anchors[currlyric] = lyrics[next]
            except Exception:
                pass
        next = UtilBot.find_next_non_blank(lyrics, currmin[0])
        chopped = lyrics[currmin[0]][1]
        found_lyric = lyrics[currmin[0]][0] + " " + lyrics[next][0] if chopped else lyrics[next][0]
        if found_lyric.startswith('['):
            found_lyric = anchors[found_lyric]
        if showguess:
            segments = [hangups.ChatMessageSegment(found_lyric),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                        hangups.ChatMessageSegment(songs[0].name)]
            bot.send_message_segments(event.conv, segments)
        else:
            bot.send_message(event.conv, found_lyric)

        return


@DispatcherSingleton.register
def record(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Record*
Usage: /record <text to record>
Usage: /record date <date to show records from>
Usage: /record list
Usage: /record search <search term>
Usage: /record strike
Usage: /record
Purpose: Store/Show records of conversations. Note: All records will be prepended by: "On the day of <date>," automatically.
""")
        bot.send_message_segments(event.conv, segments)
    else:
        import datetime

        global last_recorded, last_recorder
        directory = "Records" + os.sep + str(event.conv_id)
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = str(datetime.date.today()) + ".txt"
        filepath = os.path.join(directory, filename)
        file = None

        # Deletes the record for the day. TODO Is it possible to make this admin only?
        if ''.join(args) == "clear":
            file = open(filepath, "a+")
            file.seek(0)
            file.truncate()

        # Shows the record for the day.
        elif ''.join(args) == '':
            file = open(filepath, "a+")
            # If the mode is r+, it won't create the file. If it's a+, I have to seek to the beginning.
            file.seek(0)
            segments = [hangups.ChatMessageSegment(
                'On the day of ' + datetime.date.today().strftime('%B %d, %Y') + ':', is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            for line in file:
                segments.append(
                    hangups.ChatMessageSegment(line))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)

        # Removes the last line recorded, iff the user striking is the same as the person who recorded last.
        # TODO This isn't working properly across multiple chats.
        elif args[0] == "strike":
            if event.user.id_ == last_recorder:
                file = open(filepath, "a+")
                file.seek(0)
                file_lines = file.readlines()
                if last_recorded is not None and last_recorded in file_lines:
                    file_lines.remove(last_recorded)
                file.seek(0)
                file.truncate()
                file.writelines(file_lines)
                last_recorded = None
                last_recorder = None
            else:
                bot.send_message(event.conv, "You do not have the authority to strike from the Record.")

        # Lists every record available. TODO Paginate this?
        elif args[0] == "list":
            files = os.listdir(directory)
            segments = []
            for name in files:
                segments.append(hangups.ChatMessageSegment(name.replace(".txt", "")))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)

        # Shows a list of records that match the search criteria.
        elif args[0] == "search":
            args = args[1:]
            searched_term = ' '.join(args)
            escaped_args = []
            for item in args:
                escaped_args.append(re.escape(item))
            term = '.*'.join(escaped_args)
            term = term.replace(' ', '.*')
            if len(args) > 1:
                term = '.*' + term
            else:
                term = '.*' + term + '.*'
            foundin = []
            for name in glob.glob(directory + os.sep + '*.txt'):
                with open(name) as f:
                    contents = f.read()
                if re.match(term, contents, re.IGNORECASE | re.DOTALL):
                    foundin.append(name.replace(directory, "").replace(".txt", "").replace("\\", ""))
            if len(foundin) > 0:
                segments = [hangups.ChatMessageSegment("Found "),
                            hangups.ChatMessageSegment(searched_term, is_bold=True),
                            hangups.ChatMessageSegment(" in:"),
                            hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK)]
                for filename in foundin:
                    segments.append(hangups.ChatMessageSegment(filename))
                    segments.append(hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK))
                bot.send_message_segments(event.conv, segments)
            else:
                segments = [hangups.ChatMessageSegment("Couldn't find  "),
                            hangups.ChatMessageSegment(searched_term, is_bold=True),
                            hangups.ChatMessageSegment(" in any records.")]
                bot.send_message_segments(event.conv, segments)

        # Lists a record from the specified date.
        elif args[0] == "date":
            from dateutil import parser

            args = args[1:]
            try:
                dt = parser.parse(' '.join(args))
            except Exception as e:
                bot.send_message(event.conv, "Couldn't parse " + ' '.join(args) + " as a valid date.")
                return
            filename = str(dt.date()) + ".txt"
            filepath = os.path.join(directory, filename)
            try:
                file = open(filepath, "r")
            except IOError:
                bot.send_message(event.conv, "No record for the day of " + dt.strftime('%B %d, %Y') + '.')
                return
            segments = [hangups.ChatMessageSegment('On the day of ' + dt.strftime('%B %d, %Y') + ':', is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            for line in file:
                segments.append(hangups.ChatMessageSegment(line))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)

        # Saves a record.
        else:
            file = open(filepath, "a+")
            file.write(' '.join(args) + '\n')
            bot.send_message(event.conv, "Record saved successfully.")
            last_recorder = event.user.id_
            last_recorded = ' '.join(args) + '\n'
        if file is not None:
            file.close()


@DispatcherSingleton.register
def trash(bot, event, *args):
    bot.send_message(event.conv, "🚮")


@DispatcherSingleton.register
def spoof(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Spoof*
Usage: /spoof
Purpose: Who knows...
""")
        bot.send_message_segments(event.conv, segments)
    else:
        segments = [hangups.ChatMessageSegment('!!! CAUTION !!!', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('User ')]
        link = 'https://plus.google.com/u/0/{}/about'.format(event.user.id_.chat_id)
        segments.append(hangups.ChatMessageSegment(event.user.full_name, hangups.SegmentType.LINK,
                                                   link_target=link))
        segments.append(hangups.ChatMessageSegment(' has just been reporting to the NSA for attempted spoofing!'))
        bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def flip(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Flip*
Usage: /flip <optional: number of times to flip>
Purpose: Flips a coin.
""")
        bot.send_message_segments(event.conv, segments)
    else:
        times = 1
        if len(args) > 0 and args[-1].isdigit():
            times = int(args[-1]) if int(args[-1]) < 1000000 else 1000000
        heads, tails = 0, 0
        for x in range(0, times):
            n = random.randint(0, 1)
            if n == 1:
                heads += 1
            else:
                tails += 1
        if times == 1:
            bot.send_message(event.conv, "Heads!" if heads > tails else "Tails!")
        else:
            bot.send_message(event.conv,
                             "Winner: " + (
                                 "Heads!" if heads > tails else "Tails!" if tails > heads else "Tie!") + " Heads: " + str(
                                 heads) + " Tails: " + str(tails) + " Ratio: " + (str(
                                 Fraction(heads, tails)) if heads > 0 and tails > 0 else str(heads) + '/' + str(tails)))


@DispatcherSingleton.register
def quote(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Quote*
Usage: /quote <optional: terms to search for> \
<optional: number of quote to show>
Purpose: Shows a quote.
""")
        bot.send_message_segments(event.conv, segments)
    else:
        USER_ID = "3696"
        DEV_ID = "ZWBWJjlb5ImJiwqV"
        QUERY_TYPE = "RANDOM"
        fetch = 0
        if len(args) > 0 and args[-1].isdigit():
            fetch = int(args[-1])
            args = args[:-1]
        query = '+'.join(args)
        if len(query) > 0:
            QUERY_TYPE = "SEARCH"
        url = "http://www.stands4.com/services/v2/quotes.php?uid=" + USER_ID + "&tokenid=" + DEV_ID + "&searchtype=" + QUERY_TYPE + "&query=" + query
        soup = BeautifulSoup(request.urlopen(url))
        if QUERY_TYPE == "SEARCH":
            children = list(soup.results.children)
            numQuotes = len(children)
            if numQuotes == 0:
                bot.send_message(event.conv, "Unable to find quote.")
                return

            if fetch > numQuotes - 1:
                fetch = numQuotes
            elif fetch < 1:
                fetch = 1
            bot.send_message(event.conv, "\"" +
                             children[fetch - 1].quote.text + "\"" + ' - ' + children[
                fetch - 1].author.text + ' [' + str(
                fetch) + ' of ' + str(numQuotes) + ']')
        else:
            bot.send_message(event.conv, "\"" + soup.quote.text + "\"" + ' -' + soup.author.text)

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
def yt(bot, event, *args):
    youtube(bot, event, *args)
    
@DispatcherSingleton.register
def YouTube(bot, event, *args):
    youtube(bot, event, *args)
    
@DispatcherSingleton.register
def xfiles(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*xfiles*
Usage: /xfiles
Purpose: but what if bot is not kill
""")
        bot.send_message_segments(event.conv, segments)
    else:
        args = ['xfiles','theme']
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
def source(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Source*
Usage: /source
Purpose: Links to the GitHub
""")
        bot.send_message_segments(event.conv, segments)
    else:
        url = 'https://github.com/ShaunOfTheLive/HangoutsBot'
        segments = [hangups.ChatMessageSegment(url,
                                               hangups.SegmentType.LINK,
                                               link_target=url)]
        bot.send_message_segments(event.conv, segments)
        
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
        
@DispatcherSingleton.register
def latex(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*LaTeX*
Usage: /latex <LaTeX code>
Purpose: Renders LaTeX code to an image and sends it
""")
        bot.send_message_segments(event.conv, segments)
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
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Greentext*
Usage: /greentext <text>
Purpose: makes your text green and adds an epic maymay arrow
""")
        bot.send_message_segments(event.conv, segments)
    else:
        template = "\definecolor{4chan}{RGB}{120,153,34}{\color{4chan}>\!\!\\text{%s}}"
        args = template % ' '.join(args)
        yield from latex(bot, event, args)

@DispatcherSingleton.register
def colour(bot, event, *args):
    yield from color(bot, event, *args)
 
@DispatcherSingleton.register
def color(bot, event, *args):
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
            bot.send_message(event.conv, output)
        imageID = yield from bot._client.upload_image(filename)
        bot.send_image(event.conv, imageID)
        os.remove(filename)
    except subprocess.CalledProcessError as e:
        output = e.output.decode(encoding='UTF-8')
        if output != '':
            bot.send_message(event.conv, output)

