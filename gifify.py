import argparse
import os
import hashlib
import requests
import sys
import datetime
from moviepy.editor import *

def get_hash(name):
    """Returns the hash of the video. 
    The function calculates the hash as required by the API 
    following the format given in the documentation.
    
    :param name: The path of the video
    
    :returns: Hash composed by taking the first 
    and the last 64kb of the video file, putting all 
    together and generating a md5 of the resulting data.
    """
    readsize = 64 * 1024
    
    with open(name, 'rb') as f:
        size = os.path.getsize(name)
        data = f.read(readsize)
        f.seek(-readsize, os.SEEK_END)
        data += f.read(readsize)
    
    return hashlib.md5(data).hexdigest()

def get_subtitles(movie):
    """Fetches the subtitles from the API for the movie.
    
    :param movie: Absolute path to the movie.
    
    :returns: Response returned by the API.
    """
    base_url = "http://api.thesubdb.com/"
    user_agent = "SubDB/1.0 (Syn3rman/0.1; http://github.com/Syn3rman)"

    headers = {"User-Agent": user_agent}

    params = {
        "action": "download",
        "hash": get_hash(movie),
        "language": "en"
    }

    res = requests.get(base_url, headers=headers, params=params)

    if not res.text:
        print("Subtitles not found")
        sys.exit(0)
        
    return res.text

def remove_special_chars(word):
    """Removes special characters from a word to make lookup easier"""
    
    special_chars = [",", "?", "-", "!", "."]
    word = word.lower()
    
    for char in special_chars:
        while char in word:
            word = word.replace(char, "")
    
    return word

def time_in_seconds(ts):
    tso = datetime.datetime.strptime(ts, "%H:%M:%S,%f")
    return tso.hour*3600 + tso.minute*60 + tso.second
    
def create_index(parsed_response):
    """Index the timestamp at which each word occurs.
    
    :param parsed_response: The API response after replacing
    new line characters with spaces.
    
    :returns: Index of the form { word: [all timestamps where it occurs] }
    """
    index = {}

    for lines in parsed_response:
        line = lines.split(" ")
        
        try:
            dialogue = " ".join(line[4:])
            start = line[1]
            starts = time_in_seconds(start)
            tss[starts] = 0
            
            for word in dialogue.split(" "):
                parsed_word = remove_special_chars(word)
    
                if index.get(parsed_word,""):
                    index[parsed_word].append(starts)
                else:
                    index[parsed_word] = [starts]    
        except:
            break
            
    return index

def lookup_index(index, sentence):
    """Given a quote/sentence, find 
    all the occurences of all the words.
    
    :param index: The index to be searched
    :param sentence: The quote/sentence to be searched.
    
    :returns: List of lists with each sublist having all the timestamps at which the word occurs in the movie.
    """
    result = []
    words = sentence.split(" ")
    for word in words:
        parsed_word = remove_special_chars(word)
        start_times = index.get(parsed_word, [])
        result.append(start_times)
    return result

def find_start_time(ts):
    """Populate tss and get the most likely timestamps at 
    which the quote appears in the movie.

    :param ts: 

    :returns: Best 3 start times along with confidence score
    """
    ts.sort(key = len, reverse = True)    
    for t in ts:
        for i in t:
            tss[i] += 1/len(t)
    res = {k: v for k, v in sorted(tss.items(), key=lambda item: item[1], reverse = True)}
    best_sol = {k: res[k] for k in list(res)[:3]}
    return best_sol

def make_gif(start_time, end_time, output_file):
    video = VideoFileClip(movie).subclip(list(map(int, start_time.split(":"))), list(map(int, end_time.split(":"))))
    video = video.resize(0.5)
    video.write_gif(output_file)


parser = argparse.ArgumentParser()

parser.add_argument("--quote", type = str, dest = "quote", help = "Quote you want to find")
parser.add_argument("-o", type = str, dest = "out_file", help = "Save gif as")
parser.add_argument("movie", type = str, help = 'Absolute path of the movie')
parser.add_argument("--start", type = str, dest = "starts_at", help = "Start time for gif")
parser.add_argument("--end", type = str, dest = "ends_at", help = "End time for gif")

args = parser.parse_args()

# tss is a global data structure to store how many words 
# have the same timestamp (weighted).
# Words that frequently occur in the movie are given lower 
# weights than those that occur less frequently because 
# these are more likely to help in finding the timestamp 
# at which the quote is present.
tss = {}

movie = args.movie
sentence = args.quote
output_file = args.out_file if args.out_file is not None else "op.gif"

if sentence is not None:
    if args.starts_at is None and args.ends_at is None:
        raw_response = get_subtitles(movie)
        parsed_response = raw_response.replace('\n', ' ').replace('\r', '').split("  ")

        index = create_index(parsed_response)
        ts = lookup_index(index, sentence)
        res = find_start_time(ts)

        for key, val in res.items():
            print("Time: {}, confidence score: {}".format(str(datetime.timedelta(seconds = key)), val))

        starts_at = str(datetime.timedelta(seconds = list(res.keys())[0]))
        ends_at = str(datetime.timedelta(seconds = list(res.keys())[0] + 4))
        make_gif(starts_at, ends_at, output_file)

    else:
        print("Providing the start and end time overrides finding the quote.")
        make_gif(args.starts_at, args.ends_at, output_file)
else:
    if args.starts_at is None or args.ends_at is None:
        print("Need to pass both start and end times for gif.")
        sys.exit(0)
    make_gif(args.starts_at, args.ends_at, output_file)