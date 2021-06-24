import sys
import datetime
import config
import json
import uuid
import time
import requests
from os import makedirs
from os.path import join
from gallery_dl import job
from gallery_dl import config as dlconfig
from gallery_dl.extractor.message import Message
from io import StringIO
from html.parser import HTMLParser

from flask import current_app

from ..internals.database.database import get_conn, get_raw_conn, return_conn
from ..lib.artist import index_artists, is_artist_dnp, update_artist
from ..lib.post import post_flagged, post_exists, delete_post_flags, move_to_backup, restore_from_backup, delete_backup
from ..internals.utils.download import download_file, DownloaderException
from ..internals.utils.proxy import get_proxy
from ..internals.utils.logger import log
from ..internals.utils.utils import parse_date

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d)
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def import_posts(import_id, key):
    dlconfig.set(('output'), "mode", "null")
    dlconfig.set(('extractor', 'subscribestar'), "cookies", {
        "auth_token": key
    })
    dlconfig.set(('extractor', 'subscribestar'), "proxy", get_proxy())
    j = job.DataJob("https://subscribestar.adult/feed") 
    j.run()
    
    user_id = None
    for message in j.data:
        backup_path = None
        try:
            if message[0] == Message.Directory:
                post = message[-1]

                user_id = post['author_name']
                post_id = post['post_id']
                file_directory = f"files/subscribestar/{user_id}/{post_id}"
                attachments_directory = f"attachments/subscribestar/{user_id}/{post_id}"
                
                if is_artist_dnp('subscribestar', user_id):
                    log(import_id, f"Skipping post {post_id} from user {user_id} is in do not post list")
                    continue

                if post_exists('subscribestar', user_id, str(post_id)) and not post_flagged('subscribestar', user_id, str(post_id)):
                    log(import_id, f'Skipping post {post_id} from user {user_id} because already exists')
                    continue

                if post_flagged('subscribestar', user_id, str(post_id)):
                    backup_path = move_to_backup('patreon', user_id, post_id)

                log(import_id, f"Starting import: {post_id}")

                stripped_content = strip_tags(post['content'])
                post_model = {
                    'id': str(post_id),
                    '"user"': user_id,
                    'service': 'subscribestar',
                    'title': (stripped_content[:60] + '..') if len(stripped_content) > 60 else stripped_content,
                    'content': post['content'],
                    'embed': {},
                    'shared_file': False,
                    'added': datetime.datetime.now(),
                    'published': post['date'],
                    'edited': None,
                    'file': {},
                    'attachments': []
                }

                for attachment in list(filter(lambda msg: post_id == msg[-1]['post_id'] and msg[0] == Message.Url, j.data)):
                    if (len(post_model['file'].keys()) == 0):
                        filename, _ = download_file(
                            join(config.download_path, file_directory),
                            attachment[-1]['url'],
                            name = attachment[-1]['filename'] + '.' + attachment[-1]['extension']
                        )
                        post_model['file']['name'] = attachment[-1]['filename'] + '.' + attachment[-1]['extension']
                        post_model['file']['path'] = f'/{file_directory}/{filename}'
                    else:
                        filename, _ = download_file(
                            join(config.download_path, attachments_directory),
                            attachment[-1]['url'],
                            name = attachment[-1]['filename'] + '.' + attachment[-1]['extension']
                        )
                        post_model['attachments'].append({
                            'name': attachment[-1]['filename'] + '.' + attachment[-1]['extension'],
                            'path': f'/{attachments_directory}/{filename}'
                        })
                
                post_model['embed'] = json.dumps(post_model['embed'])
                post_model['file'] = json.dumps(post_model['file'])
                for i in range(len(post_model['attachments'])):
                    post_model['attachments'][i] = json.dumps(post_model['attachments'][i])

                columns = post_model.keys()
                data = ['%s'] * len(post_model.values())
                data[-1] = '%s::jsonb[]' # attachments
                query = "INSERT INTO posts ({fields}) VALUES ({values}) ON CONFLICT (id, service) DO UPDATE SET {updates}".format(
                    fields = ','.join(columns),
                    values = ','.join(data),
                    updates = ','.join([f'{column}=EXCLUDED.{column}' for column in columns])
                )
                conn = get_raw_conn()
                cursor3 = conn.cursor()
                cursor3.execute(query, list(post_model.values()))
                conn.commit()
                return_conn(conn)

                update_artist('subscribestar', user_id)
                delete_post_flags('subscribestar', user_id, str(post_id))

                if (config.ban_url):
                    requests.request('BAN', f"{config.ban_url}/{post_model['service']}/user/" + post_model['"user"'])

                if backup_path is not None:
                    delete_backup(backup_path)
                log(import_id, f"Finished importing {post_id} from user {user_id}", to_client = False)
        except Exception:
            log(import_id, f"Error while importing {post_id} from user {user_id}", 'exception')

            if backup_path is not None:
                restore_from_backup('fanbox', user_id, post_id, backup_path)
            continue
    
    log(import_id, f"Finished scanning for posts.")
    index_artists()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        import_posts(str(uuid.uuid4()), sys.argv[1])
    else:
        print('Argument required - Login token')
