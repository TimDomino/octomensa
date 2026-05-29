#!/opt/mensa/python/bin/python
import argparse
import datetime
import requests
import bs4
import os
import shutil
import sys
import time
import json

from selenium import webdriver
from selenium.webdriver.common.by import By

mensa_url = 'https://www.studierendenwerk-aachen.de/speiseplaene/$(MENSA_NAME)-w$(LANG_MODIFIER).html'
lang_modifiers = {'en': '-en', 'de': ''}

mattermost_post_url = 'https://mattermost.vr.rwth-aachen.de/api/v4/posts'
mattermost_upload_url = 'https://mattermost.vr.rwth-aachen.de/api/v4/files'
mattermost_channel_id = '44n1ysibmtbxme65pmhbwoofzy'  # test channel
mattermost_token = open('secret/mattermost-token.txt', 'r').readline().replace('\n','')

mensa_names = {'vita': ('vita', 'Mensa Vita'),
               'acad': ('academica', 'Mensa Academica'),
               'ahor': ('ahornstrasse', 'Mensa Ahornstraße'),
               'temp': ('templergraben', 'Bistro Templergraben'),
               'baye': ('bayernallee', 'Mensa Bayernallee'),
               'kmac': ('kmac', 'Mensa KMAC'),
               'eupe': ('eupenerstrasse', 'Mensa Eupener Straße'),
               'sued': ('suedpark', 'Mensa Südpark'),
               'juel': ('juelich', 'Mensa Jülich')}

weekdays = {'en': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            'de': ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']}

date_format = '%d.%m.%Y'
screenshot_directory = 'output/'

today = datetime.datetime.today().replace(
    hour=0, minute=0, second=0, microsecond=0)


class MenuItem:
    item_type = ""
    description = ""
    price = ""
    vegetarian = False
    vegan = False

    def __init__(self, item_type, description, price, vegetarian=False, vegan=False):
        self.item_type = item_type
        self.description = description
        self.price = price
        self.vegetarian = vegetarian
        self.vegan = vegan

    def __str__(self, compact=False):
        leader = ''
        if compact:
            leader = '- '

        if compact:
            return f'{leader}{self.description} | *{self.price}*\n'
        else:
            return f'**{self.item_type}**\n{leader}{self.description}\n*{self.price}*\n\n'


class DayMenu:
    date = datetime.datetime.today()
    language = 'en'
    menu_items = []

    def __init__(self, date, language):
        self.date = date
        self.language = language
        self.menu_items = []

    def __str__(self, vegetarian=False, vegan=False, compact=False):
        final_string = f'{weekdays[self.language][self.date.weekday()]}, {self.date.strftime(date_format)}\n'
        final_string += (len(final_string)+1) * '-' + '\n'

        for menu_item in self.menu_items:
            if not (vegetarian and menu_item.vegetarian == False) and \
               not (vegan and menu_item.vegan == False):
                final_string += menu_item.__str__(compact)

        return final_string


def main():
    arguments = parse_command_arguments()

    get_url = mensa_url.replace(
        '$(MENSA_NAME)', mensa_names[arguments.mensa][0])
    get_url = get_url.replace(
        '$(LANG_MODIFIER)', lang_modifiers[arguments.lang])

    menu_list = get_all_menus(get_url, arguments.lang)
    relative_list = get_relative_list(menu_list)
    print_list = get_print_list(
        relative_list, arguments.num_past, arguments.num_future)

    if print_list.count(True) > 0:

        if arguments.screenshot:
            screenshot_list = take_screenshots(get_url, menu_list, relative_list, print_list,
                                               screenshot_directory, arguments.mensa)
            if arguments.upload:
                post_mattermost('', screenshot_list)

        else:
            print_string = print_relevant_menus(
                menu_list, print_list, arguments.vegetarian, arguments.vegan, arguments.long)

            if arguments.upload:
                post_mattermost(print_string)
            else:
                print(print_string)


def parse_command_arguments():
    list_of_mensas = 'Available locations are '
    for key in mensa_names.keys():
        list_of_mensas += f'{mensa_names[key][1]} ({key}), '
    list_of_mensas = list_of_mensas[:-2]

    parser = argparse.ArgumentParser(
        prog='mensa.py',
        description="Display what's on the menu at one of Aachen's finest dining places",
        epilog=list_of_mensas)
    parser.add_argument('-m', '--mensa', help="the mensa to retrieve the menu for, default is 'vita'",
                        choices=mensa_names.keys(), default=list(mensa_names.keys())[0])
    parser.add_argument('-p', '--past', type=int, help="print previous NUM_PAST menus, default is all",
                        nargs='?', const=20, default=0, dest='num_past')
    parser.add_argument('-f', '--future', type=int, help="print next NUM_FUTURE menus, default is all",
                        nargs='?', const=20, default=0, dest='num_future')
    parser.add_argument('-v', '--vegetarian', action='store_true',
                        help="only show vegetarian options")
    parser.add_argument('-vv', '--vegan', action='store_true',
                        help="only show vegan options")
    parser.add_argument('-l', '--long', action='store_true',
                        help="use long instead of compact output, including dish category")
    parser.add_argument('-lg', '--lang', help="select the language to retrieve, default is 'en'",
                        choices=['en', 'de'], default='en')
    parser.add_argument('-s', '--screenshot', action='store_true',
                        help="save a screenshot of each selected menu")
    parser.add_argument('-u', '--upload', action='store_true',
                        help="upload the result to Mattermost")

    return parser.parse_args()


def get_all_menus(url, lang_shorthand):
    soup = download_current_menu_data(url)

    menu_root_nodes = soup.find_all('div', 'preventBreak')
    menus = []

    for menu_root in menu_root_nodes:
        day_menu = get_day_menu(menu_root, lang_shorthand)
        menus.append(day_menu)

    return menus


def download_current_menu_data(url):
    response = requests.get(url)
    response.encoding = response.apparent_encoding

    if response.status_code == 200:
        return bs4.BeautifulSoup(response.text, 'html.parser')

    else:
        print(
            f'Error retrieving page. Response code is: {response.status_code}')
        sys.exit(1)


def get_day_menu(menu_root_node, language):
    date_string = get_text_or_default(menu_root_node.find('a'))
    date_string = date_string.split(',')[1].lstrip()  # remove weekday
    datetime_object = datetime.datetime.strptime(date_string, date_format)
    day_menu = DayMenu(datetime_object, language)

    menu_table = menu_root_node.find('table', 'menues')

    for menu_item_row in menu_table.find_all('tr'):
        item_type = get_text_or_default(
            menu_item_row.find('span', 'menue-category'))
        item_description = get_text_or_default(
            menu_item_row.find('span', 'expand-nutr'))
        item_price = get_text_or_default(menu_item_row.find(
            'span', 'menue-price'), default='Unknown Price')
        item_nutrition = get_nutrition(menu_item_row)
        menu_item = MenuItem(item_type, item_description,
                             item_price, item_nutrition[0], item_nutrition[1])
        day_menu.menu_items.append(menu_item)

    return day_menu


def get_text_or_default(html, default=""):
    return_string = ""

    try:
        # remove letters in <sup>-tag (allergene letters)
        copy_html = html
        for tag in copy_html.find_all('sup'):
            tag.replace_with('')

        return_string = copy_html.get_text()

        # clean input string for undesired characters
        return_string = return_string.replace('\n', '')
        return_string = return_string.replace('+', '')

        # remove duplicate spaces
        return_string = ' '.join(return_string.split())
    except:
        return_string = default

    return return_string


def get_nutrition(html):
    is_vegetarian = 'OLV' in html['class']
    is_vegan = 'vegan' in html['class']
    return (is_vegetarian, is_vegan)


def get_relative_list(menu_list):
    relative_list = list(map(lambda menu: (menu.date-today).days, menu_list))
    relative_list = list(map(lambda id: sign(id), relative_list))
    past_days = relative_list.count(-1)
    future_days = relative_list.count(1)

    for i in range(past_days):
        relative_list[i] = -past_days
        past_days = past_days - 1

    for j in range(future_days):
        relative_list[-(j+1)] = future_days
        future_days = future_days - 1

    return relative_list


def sign(x):
    if x < 0:
        return -1
    elif x > 0:
        return 1
    else:
        return 0


def get_print_list(relative_list, num_past, num_future):
    print_list = [False for i in range(len(relative_list))]

    for i in range(len(relative_list)):
        if (relative_list[i] < 0 and relative_list[i] >= -num_past) or \
           (relative_list[i] > 0 and relative_list[i] <= num_future) or \
           (relative_list[i] == 0):

            print_list[i] = True

    return print_list


def print_relevant_menus(menu_list, print_list, vegetarian, vegan, long_output):
    output_print_string = ''

    for i in range(len(print_list)):
        if print_list[i]:
            output_print_string += menu_list[i].__str__(vegetarian=vegetarian,
                                                        vegan=vegan, compact=not long_output) + '\n'

    return output_print_string


def take_screenshots(url, menu_list, relative_list, print_list, output_dir, filename_prefix):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless=new")
    browser = webdriver.Firefox(options=options)
    browser.get(url)
    menu_accordion_items = browser.find_elements(
        By.CSS_SELECTOR, '.preventBreak')

    screenshot_list = []
    for i in range(len(print_list)):
        if print_list[i]:

            # only click if not today because it is open already otherwise
            if relative_list[i] != 0:
                menu_accordion_items[i].click()
                time.sleep(1)
            file_name = f'{filename_prefix}-{menu_list[i].date.strftime("%Y-%m-%d")}'
            file_path = f'{output_dir}/{file_name}.png'
            menu_accordion_items[i].screenshot(file_path)
            screenshot_list.append(file_path)

    browser.close()
    return screenshot_list


def post_mattermost(message, attachments=[]):
    if len(attachments) > 5:  # terminate when too many attachments are provided
        print('Error: Upload of more than five attachments is not supported by Mattermost')
        sys.exit(1)
    elif len(attachments) == 0 and message == '':  # return when nothing to post
        return

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {mattermost_token}"})

    upload_file_ids = []

    for file_name in attachments:
        upload_form_data = {
            'channel_id': ('', mattermost_channel_id),
            'client_ids': ('', file_name),
            'files': (open(file_name, 'rb')),
        }
        response = session.post(mattermost_upload_url, files=upload_form_data)
        upload_file_ids.append(response.json()['file_infos'][0]['id'])

    post_data = {
        'channel_id': mattermost_channel_id,
        'message': message,
        'file_ids': upload_file_ids
    }
    response = session.post(mattermost_post_url, data=json.dumps(post_data))


if __name__ == '__main__':
    main()
