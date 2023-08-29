"""
goms

Usage:
  goms
    [--log-level=<log_lvl>]
  goms -h | --help

Options:
  --log-level=<log_lvl>     Logging level [default: debug].
  -h --help                 Show this screen.
"""

from docopt import docopt
import json
import logging
import music_tag
from os import makedirs
from pathlib import Path
import subprocess

from msmusic.logging import logger


YOUTUBEDL_PATH = r'D:\youtubedl\youtube-dl.exe'

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    
    while True:
        # Read output from the process
        output = process.stdout.readline()
        
        # Break the loop if the process is done
        if output == '' and process.poll() is not None:
            break
        
        if output:
            logger.info(output.strip())
    
    # Capture any error output
    stderr_output = process.stderr.read().strip()
    if stderr_output:
        logger.error(stderr_output)

        raise RuntimeError(stderr_output)


if __name__ == '__main__':
    cli_params = docopt(__doc__)
    if cli_params["--log-level"]:
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        for ll in loggers:
            ll.setLevel(cli_params["--log-level"].upper())
    logger.debug(cli_params)

    logger.debug("Hello World")

    maplebgm_db_dir = Path(r'D:\repos\maplebgm-db\bgm')
    if not maplebgm_db_dir.exists():
        logger.error(f'MapleBGM DB dir does not exist at: {maplebgm_db_dir}')
        exit(-1)

    youtubedl_dir = Path(r'D:\youtubedl\bh\MapleStory BGM - The Complete Collection')
    if not youtubedl_dir.exists():
        makedirs(youtubedl_dir, exist_ok=True)
        # logger.error(f'Youtube content dir does not exist at: {youtubedl_dir}')
        # exit(-2)

    for album_fp in maplebgm_db_dir.glob('**/*.json'):
        logger.debug(f'Inspecting: {album_fp}')

        with open(album_fp, 'r') as album_fin:
            album_data = json.load(album_fin)

        for song_metadata in album_data:
            filename = song_metadata['filename']
            description = song_metadata['description']
            title = song_metadata['metadata']['title']
            youtube_id = song_metadata['youtube']
            logger.debug(f'Looking at filename: "{filename}", title: "{title}", description: "{description}"')

            if not youtube_id:
                logger.info('No youtube ID found. Will skip.')
                continue

            album_dir = youtubedl_dir / album_fp.stem
            makedirs(album_dir, exist_ok=True)

            # Move any already downloaded file at main folder into its album folder.
            for music_fp in Path(youtubedl_dir).glob(f'{title}.*'):
                music_fp.rename(album_dir / music_fp.name)
                break

            # Rename any already downloaded file to use its database filename instead of title name.
            for music_fp in Path(album_dir).glob(f'{title}.*'):
                full_filename = filename + music_fp.suffix
                if music_fp.name == full_filename:
                    continue
                music_fp.rename(album_dir / full_filename)
                break

            # Retrieve bgm if we don't already have it.
            cmd = f'{YOUTUBEDL_PATH} https://www.youtube.com/watch?v={youtube_id} -x --audio-quality 0 -o "{album_dir}\{filename}.%(ext)s"'
            found_music_fp = None
            for music_fp in Path(album_dir).glob(f'{filename}.*'):
                found_music_fp = music_fp
                break
            else:
                run_command(cmd)
                for music_fp in Path(album_dir).glob(f'{filename}.*'):
                    found_music_fp = music_fp
                    break

            # Rename .opus extensions to .ogg for compatibility.
            for music_fp in Path(album_dir).glob(f'{filename}.*'):
                if music_fp.suffix.lower() == ".opus":
                    new_ogg_fp = album_dir / (music_fp.stem + ".ogg")
                    music_fp.rename(new_ogg_fp)
                    found_music_fp = new_ogg_fp

            # Fix up bgm metadata.
            if found_music_fp:
                music = music_tag.load_file(found_music_fp)

                music["title"] = song_metadata['metadata']["title"]
                music["year"] = song_metadata['metadata']["year"]
                music["artist"] = song_metadata['metadata']["artist"]
                music["albumArtist"] = song_metadata['metadata']["albumArtist"]

                music['comment'] = song_metadata['description']
                # music['date'] = song_metadata['date']

                music['album'] = f'MapleStory {album_fp.stem}'

                music.save()

            logger.debug("Processed...")
