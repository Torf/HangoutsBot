import json
from urllib import parse, request
import re
import html
import os
import asyncio
from datetime import timedelta, datetime
from fractions import Fraction
import glob
import random
import threading
from dateutil import parser
import requests
import errno
from glob import glob
import subprocess

from bs4 import BeautifulSoup
import hangups

from Core.Commands.Dispatcher import DispatcherSingleton
from Core.Util import UtilBot

@DispatcherSingleton.register
def define(bot, event, *args):
    """
    *Define:*
    Usage: /define <word to search for> <optional: definition number [defaults to 1] OR * to show all definitions>
    Usage: /define <word to search for> <start index and end index in form of int:int (e.g., /define test 1:3)>
    Purpose: Show definitions for a word.
    """
    yield from bot.send_typing(event.conv)
    if args[-1].isdigit():
        definition, length = UtilBot.define(' '.join(args[0:-1]), num=int(args[-1]))
        segments = [hangups.ChatMessageSegment(' '.join(args[0:-1]).title(), is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        definition.replace('\n', ''))]
        yield from bot.send_message_segments(event.conv, segments)
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
            yield from bot.send_message(event.conv, "Invalid usage for /define.")
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
            yield from bot.send_message_segments(event.conv, definition_segments)
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
    yield from bot.send_typing(event.conv)
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

        yield from bot.send_message_segments(event.conv, segments)
    except PageError:
        yield from bot.send_message(event.conv, "Couldn't find \"{}\". Try something else.".format(' '.join(args)))


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
    yield from bot.send_typing(event.conv)
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

    yield from bot.send_message_segments(event.conv, [hangups.ChatMessageSegment('Result:', is_bold=True),
                                           hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                                           hangups.ChatMessageSegment(soup.title.string, hangups.SegmentType.LINK,
                                                                      link_target=url)])


@DispatcherSingleton.register
def udefine(bot, event, *args):
    if ''.join(args) == '?':
        segments = UtilBot.text_to_segments("""\
*Urbanly Define*
Usage: /udefine <word to search for> \
<optional: definition number [defaults to 1st]>
Purpose: Define a word.
""")
        yield from bot.send_message_segments(event.conv, segments)
    else:
        yield from bot.send_typing(event.conv)
        api_host = 'http://urbanscraper.herokuapp.com/search/'
        num_requested = 0
        returnall = False
        if len(args) == 0:
            yield from bot.send_message(event.conv, "Invalid usage of /udefine.")
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
                yield from bot.send_message(event.conv, error_response)
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
                yield from bot.send_message_segments(event.conv, segments)
            else:
                segments = [hangups.ChatMessageSegment(' '.join(args), is_bold=True),
                            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                            hangups.ChatMessageSegment(result + ' [{0} of {1}]'.format(
                                num_requested + 1, len(result_list)))]
                yield from bot.send_message_segments(event.conv, segments)

