#!/usr/bin/env python3
import assemblyai as aai
import sys
import os
import re
import time
import csv

# import pdb


def confirmsub(match, replace, line, count=0, flags=re.NOFLAG):
    """
    Interactively prompt the user to accept, reject, or edit a string change in line.
    It's basically re.replace(), but with interactive prompting.

    Args:
        match: Regex to match
        replace: String to replace with match
        line: Search string
        count: Number of replacements; def: all occurrences
        flags: Regex flag; def: no flag

    Returns: line
    """
    try:
        if re.search(match, line, flags):
            linemod = re.sub(match, replace, line, count, flags)
            print(f'Applying rule {match} -> {replace} (flag: {flags})')
            print(f' EXISTING: {line}')
            print(f'SUGGESTED: {linemod}')
            usersel = input('[Yne] ')
            if usersel.lower().startswith('n'):
                return line
            elif usersel.lower().startswith('e'):
                customline = input('Enter desired line: ')
                if len(customline) == 0:
                    # User didn't enter a custom line, return the original line
                    return line
                else:
                    return customline
            else:
                # Default to accept suggested edit
                return linemod
    except re.error:
        sys.stderr.write(f'Regex error in rule {match}; skipping')
    return line


def captionfixup(captions, rulescsv='subtitle-fixup.csv'):
    """
    Take a SRT file as a list of lines and a CSV rules file of
    findre,replace,flags and make all replacements, prompting the user to
    accept or reject edits.

    Args:
        captions: A list of lines from the srt captions file as a list
        rulescsv: A CSV file of regex rules: match,replace,flags

    """
    assert type(captions) is list, 'captions must be a list'

    rules = []
    captionsmod = []
    with open(rulescsv, mode='r') as rulesfp:
        rules = list(csv.DictReader(rulesfp))
        for caption in captions:
            for rule in rules:
                # print(f'Checking rule {rule["match"]}')
                try:
                    flags = int(rule['flags'])
                except TypeError:
                    flags = 0
                caption = confirmsub(rule['match'], rule['replace'], caption, count=0, flags=flags)
            captionsmod.append(caption)
    return captionsmod


if (__name__ == '__main__'):

    if (len(sys.argv) != 3 and len(sys.argv) != 4):
        print('Automatically generate captions for an audio/video file using assembly.ai')
        print('with match/replace rules.\n')
        print(f'Usage: {os.path.basename(sys.argv[0])} [media file] [fixup rules.csv] (boost words.txt)\n')
        print('Rules file must consist of matchregex,replacestring,regex flag(s) (no headers).')
        print('Optional boost words file, one per line.')
        sys.exit(0)

    if os.getenv('AAIKEY') is None:
        print('Must set environment key AAIKEY to Assembly AI API key value.')
        sys.exit(0)

    aai.settings.api_key = os.getenv('AAIKEY')
    if (len(sys.argv) == 4):
        with open(sys.argv[3], 'r') as f:
            boostwords = f.read().splitlines()
    else:
        boostwords = []

    config = aai.TranscriptionConfig(
            word_boost=boostwords,
            boost_param='high')
    transcriber = aai.Transcriber(config=config)

    print('Transcribing.')
    transcript = transcriber.transcribe(sys.argv[1])
    while transcript.status != 'completed':
        print(f'Transcribing, status: {transcript.status}. Please wait.')
        if (transcript.status == 'error'):
            print(f'Error in transcription: {transcript.error}')
            sys.exit(-1)
        time.sleep(3)

    print(f'\nTranscription complete. Validating captions using {sys.argv[2]} rules.')
    captions = transcript.export_subtitles_srt()
    fixedcaptions = captionfixup(captions.split('\n'))

    print('Writing output original and fixed caption files.')
    with open(f'{sys.argv[1]}-fixed.srt', 'w') as f:
        f.write('\n'.join(fixedcaptions))
    with open(f'{sys.argv[1]}-orig.srt', 'w') as f:
        f.write(captions)

    print('Done.')
