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

last_recorded, last_recorder = None, None
last_answer = {}

@DispatcherSingleton.register_unknown
def unknown_command(bot, event, *args):
    bot.send_message(event.conv,
                     '{}: Unknown command!'.format(event.user.full_name))


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

@DispatcherSingleton.register
def help(bot, event, command=None, *args):
    docstring = """
    *Current Implemented Commands:*
    {}
    Use: /<command name> ? or /help <command name> to find more information about the command.
    """.format(', '.join(sorted(DispatcherSingleton.commands.keys())))
    if command == '?' or command is None:
        bot.send_message_segments(event.conv, UtilBot.text_to_segments(docstring))
    else:
        if command in DispatcherSingleton.commands.keys():
            func = DispatcherSingleton.commands[command]
            if func.__doc__:
                bot.send_message_segments(event.conv, UtilBot.text_to_segments(func.__doc__))
            else:  # Compatibility purposes for the old way of showing help text.
                args = ['?']
                func(bot, event, *args)
        else:
            bot.send_message("The command {} is not registered.".format(command))

@DispatcherSingleton.register
def define(bot, event, *args):
    """
    *Define:*
    Usage: /define <word to search for> <optional: definition number [defaults to 1] OR * to show all definitions>
    Usage: /define <word to search for> <start index and end index in form of int:int (e.g., /define test 1:3)>
    Purpose: Show definitions for a word.
    """
    if args[-1].isdigit():
        definition, length = UtilBot.define(' '.join(args[0:-1]), num=int(args[-1]))
        segments = [hangups.ChatMessageSegment(' '.join(args[0:-1]).title(), is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        definition.replace('\n', ''))]
        bot.send_message_segments(event.conv, segments)
    elif args[-1] == '*':
        args = list(args)
        args[-1] = '1:*'
    if ':' in args[-1]:
        start, end = re.split(':', args[-1])
        try:
            start = int(start)
        except ValueError:
            start = 1
        display_all = False
        if end == '*':
            end = 100
            display_all = True
        else:
            try:
                end = int(end)
            except ValueError:
                end = 3
        if start < 1:
            start = 1
        if start > end:
            end, start = start, end
        if start == end:
            end += 1
        if len(args) <= 1:
            bot.send_message(event.conv, "Invalid usage for /define.")
            return
        query = ' '.join(args[:-1])
        definition_segments = [hangups.ChatMessageSegment(query.title(), is_bold=True),
                               hangups.ChatMessageSegment('', segment_type=hangups.SegmentType.LINE_BREAK)]
        if start < end:
            x = start
            while x <= end:
                definition, length = UtilBot.define(query, num=x)
                definition_segments.append(hangups.ChatMessageSegment(definition))
                if x != end:
                    definition_segments.append(
                        hangups.ChatMessageSegment('', segment_type=hangups.SegmentType.LINE_BREAK))
                    definition_segments.append(
                        hangups.ChatMessageSegment('', segment_type=hangups.SegmentType.LINE_BREAK))
                if end > length:
                    end = length
                if display_all:
                    end = length
                    display_all = False
                x += 1
            bot.send_message_segments(event.conv, definition_segments)
        return
    else:
        args = list(args)
        args.append("1:3")
        define(bot, event, *args)
        return


@DispatcherSingleton.register
def wiki(bot, event, *args):
    """
    *Wikipedia:*
    Usage: /wiki <keywords to search for> <optional: sentences to display [defaults to 3]>
    Purpose: Get summary from Wikipedia on keywords.
    """
    from wikipedia import wikipedia, PageError, DisambiguationError

    def summary(self, sentences=3):
        if not getattr(self, '_summary', False):
            query_params = {
                'prop': 'extracts',
                'explaintext': '',
                'exintro': '',
            }
        query_params['exsentences'] = sentences
        if not getattr(self, 'title', None) is None:
            query_params['titles'] = self.title
        else:
            query_params['pageids'] = self.pageid

        request = wikipedia._wiki_request(query_params)
        self._summary = request['query']['pages'][self.pageid]['extract']

        return self._summary

    wikipedia.WikipediaPage.summary = summary
    try:
        sentences = 3
        try:
            if args[-1].isdigit():
                sentences = args[-1]
                args = args[:-1]
            page = wikipedia.page(' '.join(args))
        except DisambiguationError as e:
            page = wikipedia.page(wikipedia.search(e.options[0], results=1)[0])
        segments = [
            hangups.ChatMessageSegment(page.title, hangups.SegmentType.LINK, is_bold=True, link_target=page.url),
            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
            hangups.ChatMessageSegment(page.summary(sentences=sentences))]

        bot.send_message_segments(event.conv, segments)
    except PageError:
        bot.send_message(event.conv, "Couldn't find \"{}\". Try something else.".format(' '.join(args)))


# TODO Sometimes, this'll just link straight to the search page. Attempting to compare the url set here with the url we
# get as a response fails more than it succeeds. Is there a way to guarantee that we either get a working link
# or that we know for sure that the link we got is a failure case?
@DispatcherSingleton.register
def goog(bot, event, *args):
    """
    *Google:*
    Usage: /goog <optional: search parameters>
    Purpose: Get a link to the first result from a Google search using the search parameters.
    """

    search_terms = " ".join(args)
    if search_terms == "" or search_terms == " ":
        search_terms = "google"
    query = parse.urlencode({'q': search_terms})
    url = 'https://www.google.com/search?%s&btnI=1' \
          % query
    headers = {
        'User-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'}
    req = request.Request(url, None, headers)
    resp = request.urlopen(req)
    soup = BeautifulSoup(resp)

    bot.send_message_segments(event.conv, [hangups.ChatMessageSegment('Result:', is_bold=True),
                                           hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                                           hangups.ChatMessageSegment(soup.title.string, hangups.SegmentType.LINK,
                                                                      link_target=url)])

@DispatcherSingleton.register
def echo(bot, event, *args):
    """
    *Echo:*
    Usage: /echo <text to echo>
    Purpose: Bot will echo the inputted text.
    """
    bot.send_message(event.conv, '{}'.format(' '.join(args)))

@DispatcherSingleton.register
def rename(bot, event, *args):
    """
    *Rename:*
    Usage: /rename <new title>
    Purpose: Changes the chat title of the room.
    """

    new_title = ' '.join(args)
    try:
        title_prefix = bot.config['conversations'][event.conv_id]['title_prefix'] + ' v. '
    except KeyError:
        title_prefix = ""
    #TODO: handle KeyError properly
    if new_title.find(title_prefix) != 0:
        new_title = title_prefix + ' '.join(args)
    if new_title != get_conv_name(event.conv):
        yield from bot._client.setchatname(event.conv_id, new_title)

@DispatcherSingleton.register
def clear(bot, event, *args):
    """
    *Clear:*
    Usage: /clear
    Purpose: Clears the current screen by displaying 16 blank lines.
    """
    segments = [hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK)]
    bot.send_message_segments(event.conv, segments)

@DispatcherSingleton.register
def mute(bot, event, *args):
    """
    *Mute:*
    Usage: /mute
    Purposes: Mutes all autoreplies.
    """
    try:
        bot.config['conversations'][event.conv_id]['autoreplies_enabled'] = False
    except KeyError:
        bot.config['conversation'][event.conv_id] = {}
        bot.config['conversation'][event.conv_id]['autoreplies_enabled'] = False
    bot.config.save()

@DispatcherSingleton.register
def unmute(bot, event, *args):
    """
    *Unmute:*
    Usage: /unmute
    Purpose: Unmutes all autoreplies.
    """
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Unmute', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /unmute'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Unmutes all non-command replies.')]
        bot.send_message_segments(event.conv, segments)
    else:
        try:
            bot.config['conversations'][event.conv_id]['autoreplies_enabled'] = True
        except KeyError:
            bot.config['conversations'][event.conv_id] = {}
            bot.config['conversations'][event.conv_id]['autoreplies_enabled'] = True
        bot.config.save()


@DispatcherSingleton.register
def status(bot, event, *args):
    """
    *Status:*
    Usage: /status
    Purpose: Shows current bot status.
    """
    segments = [hangups.ChatMessageSegment('Status:', is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment(
                    'Autoreplies: ' + ('Enabled' if bot.config['conversations'][event.conv_id][
                        'autoreplies_enabled'] else 'Disabled'))]
    bot.send_message_segments(event.conv, segments)

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
