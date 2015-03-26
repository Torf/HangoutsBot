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

reminders = []

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
def vote(bot, event, set_vote=None, *args):
    if set_vote == '?':
        segments = [hangups.ChatMessageSegment('Vote', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote <subject to vote on>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote <yea|yes|for|nay|no|against (used to cast a vote)>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote cancel'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote abstain'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /vote admin (used to start a vote for a new conversation admin)'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Starts a vote in which a 50% majority wins.')]
        bot.send_message_segments(event.conv, segments)
    else:

        # Abstains user from voting.
        if set_vote is not None and set_vote.lower() == 'abstain':
            if UtilBot.is_vote_started(event.conv_id):
                bot.send_message(event.conv, 'User {} has abstained from voting.'.format(event.user.full_name))
                if UtilBot.abstain_voter(event.conv_id, event.user.full_name):
                    bot.send_message(event.conv, "The vote has ended because all voters have abstained.")
                    return
            else:
                bot.send_message(event.conv, 'No vote currently in process to abstain from.')
                return

            # Check if the vote has ended
            vote_result = UtilBot.check_if_vote_finished(event.conv_id)
            if vote_result is not None:
                if vote_result != 0:
                    bot.send_message(event.conv,
                                     'In the matter of: "' + UtilBot.get_vote_subject(event.conv_id) + '", the ' + (
                                         'Yeas' if vote_result else 'Nays') + ' have it.')
                else:
                    bot.send_message(event.conv, "The vote ended in a tie in the matter of: {}".format(
                        UtilBot.get_vote_subject(event.conv_id)))
                UtilBot.end_vote(event.conv_id)
            return

        # Cancels the vote
        if set_vote is not None and set_vote.lower() == "cancel":
            if UtilBot.is_vote_started(event.conv_id):
                bot.send_message(event.conv, 'Vote "{}" cancelled.'.format(UtilBot.get_vote_subject(event.conv_id)))
                UtilBot.end_vote(event.conv_id)
            else:
                bot.send_message(event.conv, 'No vote currently started.')
            return

        # Starts a new vote
        if not UtilBot.is_vote_started(event.conv_id) and set_vote is not None:
            vote_subject = set_vote + ' ' + ' '.join(args)
            vote_callback = None

            # TODO Refactor this into a more easily extensible system.
            if vote_subject.lower().strip() == "admin":  # For the special Conversation Admin case.

                vote_subject = '{} for Conversation Admin for chat {}'.format(event.user.full_name,
                                                                              get_conv_name(event.conv))

                def set_conv_admin(won):
                    if won:
                        try:
                            bot.config["conversations"][event.conv_id]["conversation_admin"] = event.user.id_[0]
                        except (KeyError, TypeError):
                            bot.config["conversations"][event.conv_id] = {}
                            bot.config["conversations"][event.conv_id]["admin"] = event.user.id_[0]
                        bot.config.save()

                vote_callback = set_conv_admin

            UtilBot.set_vote_subject(event.conv_id, vote_subject)
            UtilBot.init_new_vote(event.conv_id, event.conv.users)
            if vote_callback is not None:
                UtilBot.set_vote_callback(event.conv_id, vote_callback)
            bot.send_message(event.conv, "Vote started for subject: " + vote_subject)

        # Cast a vote.
        elif set_vote is not None:
            if UtilBot.can_user_vote(event.conv_id, event.user):
                set_vote = set_vote.lower()
                if set_vote == "true" or set_vote == "yes" or set_vote == "yea" or set_vote == "for" or set_vote == "yay" or set_vote == "aye":
                    UtilBot.set_vote(event.conv_id, event.user.full_name, True)
                elif set_vote == "false" or set_vote == "no" or set_vote == "nay" or set_vote == "against":
                    UtilBot.set_vote(event.conv_id, event.user.full_name, False)
                else:
                    bot.send_message(event.conv,
                                     "{}, you did not enter a valid vote parameter.".format(event.user.full_name))
                    return

                # Check if the vote has ended
                vote_result = UtilBot.check_if_vote_finished(event.conv_id)
                if vote_result is not None:
                    if vote_result != 0:
                        bot.send_message(event.conv,
                                         'In the matter of: "' + UtilBot.get_vote_subject(event.conv_id) + '", the ' + (
                                             'Yeas' if vote_result > 0 else 'Nays') + ' have it.')
                    else:
                        bot.send_message(event.conv, "The vote ended in a tie in the matter of: {}".format(
                            UtilBot.get_vote_subject(event.conv_id)))
                    UtilBot.end_vote(event.conv_id, vote_result)
                return
            else:
                bot.send_message(event.conv_id, 'User {} is not allowed to vote.'.format(event.user.full_name))
                return

        # Check the status of a vote.
        else:
            if UtilBot.is_vote_started(event.conv_id):
                status = UtilBot.get_vote_status(event.conv_id)
                if len(status) > 1:
                    bot.send_message_segments(event.conv, UtilBot.text_to_segments('\n'.join(status)))
                else:
                    bot.send_message(event.conv, "No vote currently started.")
            else:
                bot.send_message(event.conv, "No vote currently started.")
            return
