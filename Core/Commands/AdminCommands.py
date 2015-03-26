import json
import imp
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

@DispatcherSingleton.register_hidden
def devmode(bot, event, *args):
    """
    *Development Mode:*
    Usage: /devmode <on|off>
    Purpose: When development mode is on, all outputted text will go to the Python console instead of the Hangouts chat.
    """
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Development Mode', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /devmode <on|off>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: When development mode is on, all outputted text will go to the Python console instead of the Hangouts chat.')]
        bot.send_message_segments(event.conv, segments)
    else:
        if ''.join(args) == "on":
            bot.dev = True
        else:
            bot.dev = False

@DispatcherSingleton.register_hidden
def session(bot, event, *args):
    if len(args) != 1:
        return
    if args[0] == 'save':
        if bot.chatterbot:
            filename = os.path.join('cleverbot', 'session.json')
            bot.chatterbot.save_session(filename)
            bot.send_message(event.conv, "Session saved.")
        else:
            bot.send_message(event.conv, "No session to save.")
    elif args[0] == 'load':
        filename = os.path.join('cleverbot', 'session.json')
        bot.chatterbot.load_session(filename)
        bot.send_message(event.conv, "Session loaded.")

@DispatcherSingleton.register_hidden
def ping(bot, event, *args):
    """
    *Ping:*
    Usage: /ping
    Purpose: Easy way to check if Bot is running.
    """
    bot.send_message(event.conv, 'pong')
    
@DispatcherSingleton.register
def users(bot, event, *args):
    """
    *Users:*
    Usage: /users
    Purpose: Lists all users in the current conversations.
    """
    segments = [hangups.ChatMessageSegment('Users: '.format(len(event.conv.users)),
                                           is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    for user in sorted(event.conv.users, key=lambda x: x.full_name.split()[-1]):
        link = 'https://plus.google.com/u/0/{}/about'.format(user.id_.chat_id)
        segments.append(hangups.ChatMessageSegment(user.full_name, hangups.SegmentType.LINK,
                                                   link_target=link))
        if user.emails:
            segments.append(hangups.ChatMessageSegment(' ('))
            segments.append(hangups.ChatMessageSegment(user.emails[0], hangups.SegmentType.LINK,
                                                       link_target='mailto:{}'.format(user.emails[0])))
            segments.append(hangups.ChatMessageSegment(')'))

        segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
    bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def user(bot, event, username, *args):
    """
    *User:*
    Usage: /user <user name>
    Purpose: Lists information about the specified user.
    """
    username_lower = username.strip().lower()
    segments = [hangups.ChatMessageSegment('User: "{}":'.format(username),
                                           is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    for u in sorted(bot._user_list._user_dict.values(), key=lambda x: x.full_name.split()[-1]):
        if not username_lower in u.full_name.lower():
            continue

        link = 'https://plus.google.com/u/0/{}/about'.format(u.id_.chat_id)
        segments.append(hangups.ChatMessageSegment(u.full_name, hangups.SegmentType.LINK,
                                                   link_target=link))
        if u.emails:
            segments.append(hangups.ChatMessageSegment(' ('))
            segments.append(hangups.ChatMessageSegment(u.emails[0], hangups.SegmentType.LINK,
                                                       link_target='mailto:{}'.format(u.emails[0])))
            segments.append(hangups.ChatMessageSegment(')'))
        segments.append(hangups.ChatMessageSegment(' ... {}'.format(u.id_.chat_id)))
        segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
    bot.send_message_segments(event.conv, segments)
    
@DispatcherSingleton.register_hidden
def hangouts(bot, event, *args):
    """
    *Hangouts:*
    Usage: /hangouts
    Purpose: Lists all Hangouts this Bot is currently in.
    """
    segments = [hangups.ChatMessageSegment('Currently In These Hangouts:', is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    for c in bot.list_conversations():
        s = '{} [commands: {:d}, forwarding: {:d}, autoreplies: {:d}]'.format(get_conv_name(c, truncate=True),
                                                                              bot.get_config_suboption(c.id_,
                                                                                                       'commands_enabled'),
                                                                              bot.get_config_suboption(c.id_,
                                                                                                       'forwarding_enabled'),
                                                                              bot.get_config_suboption(c.id_,
                                                                                                       'autoreplies_enabled'))
        segments.append(hangups.ChatMessageSegment(s))
        segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))

    bot.send_message_segments(event.conv, segments)

@DispatcherSingleton.register_hidden
def leave(bot, event, conversation=None, *args):
    """
    *Leave:*
    Usage: /leave
    **Purpose: Leaves the chat room.**
    """
    convs = []
    if not conversation:
        convs.append(event.conv)
    else:
        conversation = conversation.strip().lower()
        for c in bot.list_conversations():
            if conversation in get_conv_name(c, truncate=True).lower():
                convs.append(c)

    for c in convs:
        yield from c.send_message([
            hangups.ChatMessageSegment('I\'ll be back!')
        ])
        yield from bot._conv_list.leave_conversation(c.id_)

@DispatcherSingleton.register_hidden
def reload(bot, event, *args):
    """
    *Reload:*
    Usage: /reload
    Purpose: Reloads the current config file into memory.
    """
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Reload', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /reload'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Reloads current config file.')]
        bot.send_message_segments(event.conv, segments)
    else:
        bot.config.load()

@DispatcherSingleton.register_hidden
def update(bot, event, *args):
    """
    *Update:*
    Usage: /update <filename.py>
    Purpose: Reloads the given module.
    """
    if len(args) != 1:
        return
    
    name = args[0]
    try:
        fp, pathname, description = imp.find_module(name)
    except ImportError:
        bot.send_message(event.conv, "unable to locate module " + name)
        return
 
    try:
        example_package = imp.load_module(name, fp, pathname, description)
    except Exception:
        bot.send_message(event.conv, "unable to update module " + name)
    
    bot.send_message(event.conv, "successfully update module " + name)

@DispatcherSingleton.register_hidden
def quit(bot, event, *args):
    """
    *Quit:*
    Usage: /quit
    Purpose: Closes the Bot.
    """
    print('HangupsBot killed by user {} from conversation {}'.format(event.user.full_name,
                                                                     get_conv_name(event.conv, truncate=True)))
    yield from bot._client.disconnect()
    
@DispatcherSingleton.register_hidden
def config(bot, event, cmd=None, *args):
    if cmd == 'get' or cmd is None:
        config_args = list(args)
        value = bot.config.get_by_path(config_args) if config_args else dict(bot.config)
    elif cmd == 'set':
        config_args = list(args[:-1])
        if len(args) >= 2:
            bot.config.set_by_path(config_args, json.loads(args[-1]))
            bot.config.save()
            value = bot.config.get_by_path(config_args)
        else:
            yield from DispatcherSingleton.unknown_command(bot, event)
            return
    else:
        yield from DispatcherSingleton.unknown_command(bot, event)
        return

    if value is None:
        value = 'Parameter does not exist!'

    config_path = ' '.join(k for k in ['config'] + config_args)
    segments = [hangups.ChatMessageSegment('{}:'.format(config_path),
                                           is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    segments.extend(UtilBot.text_to_segments(json.dumps(value, indent=2, sort_keys=True)))
    bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register_hidden
def block(bot, event, username=None, *args):
    if not username:
        segments = [hangups.ChatMessageSegment("Blocked Users: ", is_bold=True),
                    hangups.ChatMessageSegment("\n", segment_type=hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment("No users blocked.")]
        if len(UtilBot.get_blocked_users_in_conversations(event.conv_id)) > 0:
            segments.pop()
            for user in event.conv.users:
                if UtilBot.is_user_blocked(event.conv_id, user.id_):
                    segments.append(hangups.ChatMessageSegment(user.full_name))
                    segments.append(hangups.ChatMessageSegment("\n", segment_type=hangups.SegmentType.LINE_BREAK))
            segments.pop()
        bot.send_message_segments(event.conv, segments)
        return
    username_lower = username.strip().lower()
    for u in sorted(event.conv.users, key=lambda x: x.full_name.split()[-1]):
        if not username_lower in u.full_name.lower() or event.user.is_self:
            continue

        if UtilBot.is_user_blocked(event.conv_id, u.id_):
            UtilBot.remove_from_blocklist(event.conv_id, u.id_)
            bot.send_message(event.conv, "Unblocked User: {}".format(u.full_name))
            return
        UtilBot.add_to_blocklist(event.conv_id, u.id_)
        bot.send_message(event.conv, "Blocked User: {}".format(u.full_name))
        return

