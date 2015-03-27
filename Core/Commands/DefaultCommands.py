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

@DispatcherSingleton.register_unknown
def unknown_command(bot, event, *args):
    yield from bot.send_message(event.conv, '{}: Unknown command!'.format(event.user.full_name))

@DispatcherSingleton.register_hidden
def me(bot, event, *args):
    pass

@DispatcherSingleton.register
def help(bot, event, command=None, *args):
    docstring = """
    *Current Implemented Commands:*
    {}
    Use: /<command name> ? or /help <command name> to find more information about the command.
    """.format(', '.join(sorted(DispatcherSingleton.commands.keys())))
    if command == '?' or command is None:
        yield from bot.send_message_segments(event.conv, UtilBot.text_to_segments(docstring))
    else:
        if command in DispatcherSingleton.commands.keys():
            func = DispatcherSingleton.commands[command]
            if func.__doc__:
                yield from bot.send_message_segments(event.conv, UtilBot.text_to_segments(func.__doc__))
            else:  # Compatibility purposes for the old way of showing help text.
                args = ['?']
                yield from func(bot, event, *args)
        else:
            yield from bot.send_message("The command {} is not registered.".format(command))

@DispatcherSingleton.register
def echo(bot, event, *args):
    """
    *Echo:*
    Usage: /echo <text to echo>
    Purpose: Bot will echo the inputted text.
    """
    yield from bot.send_message(event.conv, '{}'.format(' '.join(args)))

@DispatcherSingleton.register_hidden
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
    yield from bot.send_message_segments(event.conv, segments)

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
    yield from bot.send_message_segments(event.conv, segments)

