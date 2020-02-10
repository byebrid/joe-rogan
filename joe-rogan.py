"""joe-rogan.py

Script to find those Joe "Insert funny reference here" Rogan comments on 
youtube.

Use main() to write these comments to a csv. Note that the API rate limit (as 
of writing this) is 10,000 requests per day (pacific time). This means that to 
get all the comments from all 4000+ videos on this channel, the script has to 
sleep until the next day before resuming. This means that it will probably take
many days to find all the comments, and this time delay also really adds to the
issue of new uploads occurring while the script is running, presumably causing
some videos to double up.
"""
from googleapiclient.discovery import build
import googleapiclient.errors
import json
import re
import logging
import datetime
import pytz
import time
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(__file__ + '.log')
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

with open('config.json', 'r') as f:
    config = json.load(f)

API_KEY = config.get("YOUTUBE_API_KEY")
service = build(serviceName='youtube', version='v3', developerKey=API_KEY)

OUTPUT_FILE = config.get("OUTPUT_FILE", None)
if OUTPUT_FILE is None:
    OUTPUT_FILE = 'joe_rogan.json'


def get_response(service_call, method, **kwargs):
    """Returns response from youtube service and handles API rate limit by 
    sleeping until API is available again.

    Example
    -------
    service.playlistItems().list(**kwargs) can be retrieved as 
    >>> get_response(service.playlistItems(), 'list', **kwargs)

    Parameters
    ----------
    service_call: executed func()
        Terrible name but the example should give some idea of what to put 
        here.
    method: func
        Unexecuted function, to be called with ``kwargs``.
    kwargs:
        Get passed into ``method``.
    """
    f = getattr(service_call, method)

    try:
        return f(**kwargs).execute()
    except googleapiclient.errors.HttpError:
        # Getting duration of time until midnight (pacific time), which is when
        # API limit resets.
        pacific_tz = pytz.timezone('Canada/Pacific')
        now = datetime.datetime.now(pacific_tz)
        tomorrow = now + datetime.timedelta(days=1)
        midnight = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day)
        # Need both datetimes to be aware to subtract them
        midnight = pacific_tz.localize(midnight)

        seconds_until_midnight = (midnight - now).seconds + 10 # A little leeway

        logger.exception('Assuming out of API quota; Sleeping ~{seconds_until_midnight} seconds until midnight (pacific time)...')
        while True:
            time.sleep(600)
            if datetime.datetime.now(pacific_tz) > midnight:
                break

        logger.info('Done sleeping, attempting to start back up...')

        # Try the API call again
        return f(**kwargs).execute()
    except:
        logger.exception(f'get_response() failed to succesfully call API.')
        raise


def get_comments(service, video_id):
    """Generator for comments on given youtube video.
    
    Yields
    ------
    comment: str
        The html of the comment

    Parameters
    ----------
    service: youtube service
        As obtained from googleapiclient.discovery.build()
    video_id: str
        I.e. the `v` parameter in a youtube video's url.
    """
    response = get_response(service.commentThreads(), 'list',
        part='snippet', 
        textFormat='html',
        videoId=video_id,
        maxResults=100
    )

    while response:
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            yield comment

        if 'nextPageToken' in response:
            page_token = response['nextPageToken']

            response = get_response(service.commentThreads(), 'list',
                part='snippet', 
                textFormat='plainText',
                videoId=video_id,
                maxResults=100,
                pageToken=page_token
            )
        else:
            break


def get_videos_from_playlist(service, playlist_id):
    """Generates videos from a given playlist.

    This is used in get_videos_from_channel() to find all videos uploaded by a 
    given channel.
    
    Yields 
    ------
    {
        'id': <video's id>, 
        'title': <video's title>,
        'thumbnail': <video's maximum resolution thumbnail>
    }
    
    Parameters
    ----------
    service: youtube service
        As obtained from googleapiclient.discovery.build()
    playlist_id: str
        Can be found in the url of a youtube playlist.
    """
    response = get_response(service.playlistItems(), 'list',
        part='contentDetails,snippet',
        playlistId=playlist_id,
        maxResults=50
    )

    while response:
        for item in response['items']:
            id = item['contentDetails']['videoId']
            title = item['snippet']['title']
            thumbnail = item['snippet']['thumbnails']['maxres']
            yield {
                'id': id,
                'title': title,
                'thumbnail': thumbnail
            }
            
        if 'nextPageToken' in response:
            page_token = response['nextPageToken']

            response = get_response(service.playlistItems(), 'list',
                part='contentDetails',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=page_token
            )
        else:
            break


def get_videos_from_channel(service, channel_id):
    """Essentially a wrapper (but not really) for get_videos_from_playlist()

    See get_videos_from_playlist() to see return values.
    
    Parameters
    ----------
    service: 
        As obtained from googleapiclient.discovery.build()
    channel_id: str
        Can be found in the url of a youtube channel's page.
    """
    response = get_response(service.channels(), 'list',
        part='contentDetails',
        id=channel_id,
        maxResults=50
    )

    # Id for playlist of this channel's uploads
    uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    for video in get_videos_from_playlist(service=service, playlist_id=uploads_id):
        yield video


def main():
    """Note that this assumes a global youtube `service` variable for the API."""
    def write_to_file(videos):
        """Updates json file new with new ``videos``."""
        # Seeing if file already there
        try:
            with open(OUTPUT_FILE, 'r') as f:
                all_videos = json.load(f)
        except FileNotFoundError:
            all_videos = {}
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(all_videos, f)

        # Updating dict and rewriting to file
        with open(OUTPUT_FILE, 'w') as f:
            all_videos.update(videos)
            json.dump(all_videos, f)


    logger.info('Started main()!')

    # The regex used to find comments with those quotes
    joe_rogan_re = re.compile('Joe .* Rogan', flags=re.I)

    try:
        visited_videos = []
        videos = {}
        # JRE Clips youtube channel
        for i, video in enumerate(get_videos_from_channel(service=service, channel_id='UCnxGkOGNMqQEUMvroOWps6Q')):
            id = video['id']
            title = video['title']
            thumbnail = video['thumbnail']

            # May happen if new uploads while script is running
            if id in visited_videos:
                continue

            videos[title] = {
                'quotes': [],
                'thumbnail': thumbnail,
                'id': id
            }

            logger.info(f'Retrieving comments from video: {id, title}...')
            for comment in get_comments(service=service, video_id=id):
                match = joe_rogan_re.match(comment)
                if match is not None:
                    quote = match.group()
                    logger.info(f'****{quote}')
                    videos[title]['quotes'].append(quote)

            visited_videos.append(id) 

            # Can modify `i` to write to file in larger chunks
            if i % 50 == 0:
                write_to_file(videos)
                videos = {}

        # Make sure to write remaining videos to file too
        write_to_file(videos)
    except:
        logger.exception(f'Something unexpectedly went wrong!')
        raise
    
    logger.info('Succesfully finished main()!')


if __name__ == '__main__':
    main()
