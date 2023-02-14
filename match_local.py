#!/usr/bin/env python3

import os
import sys
import json
import eyed3

import dataclasses


@dataclasses.dataclass
class MusicFile:
    file_path: str
    title: str
    artist: str


def detect_duplicates(file_list: list[MusicFile]) -> tuple[list[MusicFile], list[str]]:
    """detect duplicate tracks, return a tuple (A, B).
    A is the music file list with duplicates removed,
    B is a list of files paths that can be deleted"""
    bins: dict[list] = {}
    new_list = []
    deletable_files = []
    for file in file_list:
        identifier = (file.title, file.artist)
        stat = os.stat(file.file_path)
        creation_time = stat.st_ctime
        if identifier not in bins:
            bins[identifier] = []
        bins[identifier].append((file.file_path, creation_time))
    
    for item in bins.items():
        (title, artist), file_list = item
        file_list.sort(key=lambda ls: ls[1], reverse=True)
        new_list.append(MusicFile(file_list[0][0], title, artist))
        if len(file_list) > 1:
            dups = file_list[1:]

            deletable_files.extend(map(lambda x: x[0], dups))
    return (new_list, deletable_files)


def list_music_dir(dir: str):
    """read all mp3 files in a dir and return a list containing MusicFile"""
    # filter all valid music files
    musics = os.listdir(dir)
    def is_mp3(filename) -> bool:
        name, ext = os.path.splitext(filename)
        return os.path.isfile(filename) and ext.lower() == '.mp3'

    musics = map(lambda filename: os.path.join(dir, filename), musics)
    musics = filter(is_mp3, musics)

    # parse mp3 label, build database
    music_list = []

    for music_filename in musics:
        # parse label
        audiofile = eyed3.load(music_filename)
        title = audiofile.tag.title
        artist = audiofile.tag.artist

        music_list.append(MusicFile(music_filename, title, artist))
    return music_list


def match_playlist(playlist_file: str, music_list: list[MusicFile]) -> tuple[int, int, str]:
    """match the playlist to local files, return a tuple:
    (num found, num not found, m3u8 file formatted string)"""
    
    # put music list into a quick search database
    # a file is considered match if:
    # - title matches exactly
    # - all artists appeared in the artist string

    file_db = {} # maps title+artist to file location
    artist_db = {} # maps title to list of artist strings
    for music in music_list:
        file_db[(music.title, music.artist)] = music.file_path
        if music.title not in artist_db:
            artist_db[music.title] = []
        artist_db[music.title].append(music.artist)
    
    # read playlist json
    with open(playlist_file, 'rt', encoding='utf8') as f:
        playlist = json.load(f)

    # try find each track in the playlist
    found_list = []
    not_found_list = []
    for track in playlist:
        title = track['track']
        artists = track['artists']
        artists = list(filter(lambda x: isinstance(x, str), artists))

        identifier = None

        try:
            # find all possible artists strings for this title
            artist_set = artist_db[title]
        except KeyError:
            # the title cannot be found, add to not found list
            not_found_list.append('# {} BY {}'.format(title, "AND".join(artists)))
        else:
            # find the artist string that contains all listed artists
            for combined_artists_str in artist_set:
                # check if every artist are in the combined artist string
                not_match = False
                for artist in artists:
                    if artist is None:
                        continue
                    if artist not in combined_artists_str:
                        not_match = True
                        break
                if not_match:
                    continue
                else:
                    # found, calculate the identifier
                    identifier = (title, combined_artists_str)
                    break
        
        if identifier is not None:
            found_list.append('# {} BY {}'.format(title, "AND".join(artists)))
            found_list.append(os.path.abspath(file_db[identifier]))
    
    num_found = len(found_list)
    num_not_found = len(not_found_list)

    sep = os.linesep

    found_part = sep.join(found_list)
    not_found_part = sep.join(not_found_list)
    full = found_part + sep + sep + "# Below is a list of not found tracks" + sep + sep + not_found_part

    return num_found, num_not_found, full



def do_match_local_files(music_dir: str, playlist_location: str, out_dir: str, delete_duplicates = '?'):

    playlists = None
    if os.path.isdir(playlist_location):
        playlists = os.listdir(playlist_location)
        playlists = map(lambda x: os.path.join(playlist_location, x), playlists)
        playlists = filter(
            lambda x: os.path.isfile(x) and os.path.splitext(x)[1].lower() == '.json',
            playlists)
        playlists = list(playlists)
        print(f"{len(playlists)} json files found in the folder")
        if len(playlists) == 0:
            return -1
    else:
        if os.path.splitext(playlist_location)[1] != 'json':
            print('not a json file')
            return -1
        playlists = [playlist_location]
    
    
    
    # scan music files
    music_list = list_music_dir(os.path.abspath(music_dir))
    print("{} mp3 found in music folder".format(len(music_list)))
    music_list, deletables = detect_duplicates(music_list)

    # delete duplicates?
    if len(deletables) > 0:
        if delete_duplicates == '?':
            ans = input("{} duplicates found, do you want to delete them? [y/n]:".format(len(deletables)))
            if ans.lower() == 'y':
                for delete in deletables:
                    os.remove(delete)
            print("deletion done.")
        elif delete_duplicates == 'y':
            for delete in deletables:
                os.remove(delete)
        else:
            pass  # do not delete

    # prepare out dir
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    elif not os.path.isdir(out_dir):
        print("output path is not a dir")
        return -1

    # do the matching
    for playlist in playlists:
        print("matching playlist {}".format(playlist))

        num_found, num_not_found, m3u8 = match_playlist(playlist, music_list)

        print(f"{num_found} tracks found, {num_found+num_not_found} in total")
        base_name = os.path.splitext(os.path.basename(playlist))[0]
        output_name = os.path.join(out_dir, base_name + ".m3u8")
        with open(output_name, 'wt', encoding='utf8') as f:
            f.write(m3u8)
        print("written to {}".format(output_name))

    print("all done!")
            





if __name__ == "__main__":
    import argparse

    if len(sys.argv) == 1:
        # no additional argument, just start CLI
        print("Enter the playlist json file location:")
        print("(If the location is a folder, all json files inside the folder are used)")
        playlist_location = input(">>>")
        if not os.path.exists(playlist_location):
            print("location does not exist")
            exit()
        
        print("enter the music file folder:")
        music_dir = input(">>>")

        if not os.path.isdir(music_dir):
            print("is not a dir")
            exit()
        
        print("where to store the output m3u8 file(s)?")
        out_dir = input(">>>")

        exit(do_match_local_files(music_dir, playlist_location, out_dir))
        
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('music_folder', help='the folder containing all mp3 files')
        parser.add_argument('playlist_location', help='the json playlist file or a folder containing json files')
        parser.add_argument('output_dir', help='where to store generated m3u8 files')
        
        parsed = parser.parse_args()
        
        do_match_local_files(
            parsed.music_folder,
            parsed.playlist_location,
            parsed.output_dir
            )