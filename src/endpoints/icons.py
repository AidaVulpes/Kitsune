from flask import Blueprint, redirect, current_app

import re
import cssutils
import config
import requests
import cloudscraper
from os import makedirs
from os.path import exists, join
from bs4 import BeautifulSoup

from ..internals.utils.download import download_file
from ..internals.utils.proxy import get_proxy

icons = Blueprint('icons', __name__)

@icons.route('/icons/<service>/<user>')
def import_icon(service, user):
    makedirs(join(config.download_path, 'icons', service), exist_ok=True)
    if not exists(join(config.download_path, 'icons', service, user)):
        try:
            if service == 'patreon':
                scraper = cloudscraper.create_scraper().get('https://api.patreon.com/user/' + user, proxies=get_proxy())
                data = scraper.json()
                scraper.raise_for_status()
                download_file(
                    join(config.download_path, 'icons', service),
                    data['included'][0]['attributes']['avatar_photo_url'] if data.get('included') else data['data']['attributes']['image_url'],
                    name = user
                )
            elif service == 'fanbox':
                scraper = requests.get('https://api.fanbox.cc/creator.get?userId=' + user, headers={"origin":"https://fanbox.cc"}, proxies=get_proxy())
                data = scraper.json()
                scraper.raise_for_status()
                if data['body']['user']['iconUrl']:
                    download_file(
                        join(config.download_path, 'icons', service),
                        data['body']['user']['iconUrl'],
                        name = user
                    )
                else:
                    raise IconsException()
            elif service == 'subscribestar':
                scraper = requests.get('https://subscribestar.adult/' + user, proxies=get_proxy())
                data = scraper.text
                scraper.raise_for_status()
                soup = BeautifulSoup(data, 'html.parser')
                download_file(
                    join(config.download_path, 'icons', service),
                    soup.find('div', class_='profile_main_info-userpic').contents[0]['src'],
                    name = user
                )
            elif service == 'gumroad':
                scraper = requests.get('https://gumroad.com/' + user, proxies=get_proxy())
                data = scraper.text
                scraper.raise_for_status()
                soup = BeautifulSoup(data, 'html.parser')
                sheet = cssutils.css.CSSStyleSheet()
                sheet.add("dummy_selector { %s }" % soup.select_one('.profile-picture-medium.js-profile-picture').get('style'))
                download_file(
                    join(config.download_path, 'icons', service),
                    list(cssutils.getUrls(sheet))[0],
                    name = user
                )
            else:
                with open(join(config.download_path, 'icons', service, user), 'w') as _: 
                    pass
        except IconsException:
            current_app.logger.exception(f'Exception when downloading icons for user {user} on {service}')
            with open(join(config.download_path, 'icons', service, user), 'w') as _: 
                pass
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                with open(join(config.download_path, 'icons', service, user), 'w') as _: 
                    pass
            else:
                current_app.logger.exception(f'HTTP exception when downloading icons for user {user} on {service}')
    
    response = redirect(join('/', 'icons', service, user), code=302)
    response.autocorrect_location_header = False
    return response

class IconsException(Exception):
    pass
