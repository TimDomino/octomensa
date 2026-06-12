#!/bin/python
import argparse
import datetime
import requests
import bs4
import os
import json
import schedule
import shutil
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

from src.MenuItem import MenuItem
from src.MenuList import MenuList
from src.Constants import *

script_path = os.path.dirname(__file__)

# mattermost channel ids
# 15tjecufht8s5mxcrt3u967cyy    Menza Gäng
# 44n1ysibmtbxme65pmhbwoofzy    Mensa Test

def main():
    arguments = parse_command_arguments()

    if arguments.daemon_timestring:  # run in daemon mode
        schedule.every().day.at(arguments.daemon_timestring).do(
            every_workday, arguments=arguments)
        print(f'Running in daemon mode, retrieval every workday at {arguments.daemon_timestring}')

        while True:
            schedule.run_pending()
            time.sleep(5)
    else:  # run once
        retrive_and_output(arguments)


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
    parser.add_argument('-c', '--color', action='store_true',
                        help="use colored output")
    parser.add_argument('-lg', '--lang', help="select the language to retrieve, default is 'en'",
                        choices=['en', 'de', 'bi'], default='en')
    parser.add_argument('-s', '--screenshot', action='store_true',
                        help="save a screenshot of each selected menu")
    parser.add_argument('-u', '--upload', action='store',
                        help="upload the result to Mattermost, takes the channel ID as parameter")
    parser.add_argument('-d', '--daemon', action='store',
                        help='run as daemon to retrieve plan every day at the given clock time string, e.g., 08:00', dest='daemon_timestring')

    return parser.parse_args()


def every_workday(arguments):
    today = datetime.datetime.today().replace(
        hour=0, minute=0, second=0, microsecond=0)
    print(f'Everyday callback started on {today.strftime("%A, %d/%m/%y")}')
    print(f"Today's weekday is {today.weekday()}")
    if today.weekday() < 5: # 0 is Monday, 6 is Sunday
        print('Workday. Continue.')
        retrive_and_output(arguments)
    else:
        print('Not a workday. Skip.')

    print('Everyday callback terminated')


def retrive_and_output(arguments):
    if arguments.screenshot:
        prepare_output_directory(screenshot_directory)

    if arguments.lang == 'bi':
        languages_to_process = ['de', 'en']
    else:
        languages_to_process = [arguments.lang]

    # main part: iterate through languages and create desired results
    final_message = ''
    final_file_list = []
    for lang in languages_to_process:
        (message, file_list) = process_query_for_language(lang, arguments)
        final_message += message
        final_file_list = final_file_list + file_list

    # stich images together in bilingual mode
    if arguments.lang == 'bi' and arguments.screenshot:
        print('Stiching screenshots together')
        final_file_list = stitch_screenshots(final_file_list)

    # print or post results
    if arguments.upload:
        print('Uploading result to Mattermost')
        post_mattermost(arguments.upload, final_message, final_file_list)
        print('Upload completed')
    elif len(final_message) > 0:
        print(final_message, end='') # omits newline symbol


def prepare_output_directory(output_dir):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)


def process_query_for_language(lang, arguments):
    get_url = mensa_url.replace(
        '$(MENSA_NAME)', mensa_names[arguments.mensa][0])
    get_url = get_url.replace(
        '$(LANG_MODIFIER)', lang_modifiers[lang])

    soup = download_current_menu_data(get_url, arguments.vegetarian, arguments.vegan, arguments.color)
    menu_list = get_all_menus(soup, lang)
    relative_list = get_relative_list(menu_list)
    print_list = get_print_list(
        relative_list, arguments.num_past, arguments.num_future)

    if print_list.count(True) > 0:

        if arguments.screenshot:
            screenshot_list = take_screenshots(lang, menu_list, relative_list,
                                               print_list, screenshot_directory, arguments.mensa)
            return ('', screenshot_list)

        else:
            print_string = print_relevant_menus(
                menu_list, print_list, arguments.long, arguments.color)
            return (print_string, [])

    return ('', [])


def get_all_menus(soup, lang_shorthand):
    menu_root_nodes = soup.find_all('div', 'preventBreak')
    menus = []

    for menu_root in menu_root_nodes:
        day_menu = get_day_menu(menu_root, lang_shorthand)
        menus.append(day_menu)

    return menus


def download_current_menu_data(url, vegetarian_only, vegan_only, color_highlight):
    response = requests.get(url)
    response.encoding = response.apparent_encoding

    if response.status_code == 200:
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        soup = filter_soup(soup, vegetarian_only, vegan_only)

        if color_highlight:
            soup = color_soup(soup)
        
        with open(download_site_path, 'w') as download_file:
            download_file.write(str(soup))

        return soup

    else:
        print(
            f'Error retrieving page. Response code is: {response.status_code}')
        sys.exit(1)


def filter_soup(soup, vegetarian_only, vegan_only):
    if not vegetarian_only and not vegan_only:
        return soup

    flip_odd_even = False # when removing an element, flip odd even assignment for following items

    for menu_row in soup.find_all('tr'):
        if not menu_row.has_attr('class'): # other rows related to other stuff like side dishes
            continue

        if (vegan_only and 'vegan' not in menu_row['class']) \
            or (vegetarian_only and ('vegan' not in menu_row['class'] and 'OLV' not in menu_row['class'])):
            menu_row.decompose()
            flip_odd_even = not flip_odd_even
            continue

        if menu_row.find_previous_sibling() == None: # make sure menu of each day starts on odd, even after removals
            if 'even' in menu_row['class']:
                flip_odd_even = True
            else:
                flip_odd_even = False

        if flip_odd_even: # perform the flip
            if 'odd' in menu_row['class']:
                menu_row['class'].remove('odd') 
                menu_row['class'].append('even') 
            elif 'even' in menu_row['class']:
                menu_row['class'].remove('even') 
                menu_row['class'].append('odd') 

    return soup


def color_soup(soup):
    head_tag = soup.find('head')
    link_tag = soup.new_tag('link', rel='stylesheet', href='resources/css/custom_nutr_adjust.css') 
    head_tag.append(link_tag)
    return soup


def get_day_menu(menu_root_node, language):
    date_string = get_text_or_default(menu_root_node.find('a'))
    date_string = date_string.split(',')[1].lstrip()  # remove weekday
    datetime_object = datetime.datetime.strptime(date_string, date_format)
    day_menu = MenuList(datetime_object, language)

    menu_table = menu_root_node.find('table', 'menues')

    for menu_item_row in menu_table.find_all('tr'):
        item_type = get_text_or_default(
            menu_item_row.find('span', 'menue-category'))
        item_description = get_text_or_default(
            menu_item_row.find('span', 'expand-nutr'))
        item_price = get_text_or_default(menu_item_row.find(
            'span', 'menue-price'), default='Unknown Price')
        vegetarian = 'OLV' in menu_item_row['class']
        vegan = 'vegan' in menu_item_row['class']
        menu_item = MenuItem(item_type, item_description, item_price, vegetarian, vegan)
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


def get_relative_list(menu_list):
    today = datetime.datetime.today().replace(
        hour=0, minute=0, second=0, microsecond=0)
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


def print_relevant_menus(menu_list, print_list, long_output, colored):
    output_print_string = ''

    for i in range(len(print_list)):
        if print_list[i]:
            output_print_string += menu_list[i].__str__(compact=not long_output, colored=colored) + '\n'

    return output_print_string


def take_screenshots(lang, menu_list, relative_list, print_list, output_dir, filename_prefix):
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    browser = webdriver.Firefox(options=options)
    browser.get('file://' + download_site_path)
    menu_accordion_items = browser.find_elements(
        By.CSS_SELECTOR, '.preventBreak')

    screenshot_list = []
    for i in range(len(print_list)):
        if print_list[i]:

            if not (len(screenshot_list) == 0 and relative_list[i] == 0):  # if today is first screenshot, then do not click
                menu_accordion_items[i].click()
                time.sleep(1)
                
            file_name = f'{filename_prefix}-{menu_list[i].date.strftime("%Y-%m-%d")}-{lang}'
            file_path = f'{output_dir}/{file_name}.png'
            menu_accordion_items[i].screenshot(file_path)
            screenshot_list.append(file_path)

    browser.quit()
    return screenshot_list


def stitch_screenshots(screenshot_list):
    output_file_list = []

    for file_name in screenshot_list:
        if '-de.png' in file_name:
            second_file_name = file_name.replace('-de.png', '-en.png')
            stitched_file_name = file_name.replace('-de.png', '-bi.png')
            subprocess.run(['montage', file_name, second_file_name, '-tile', '2x1', '-geometry',
                           '+7+0', '-gravity', 'North', '-background', 'none', stitched_file_name])
            output_file_list.append(stitched_file_name)

    return output_file_list


def post_mattermost(channel_id, message, attachments=[]):
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
            'channel_id': ('', channel_id),
            'client_ids': ('', file_name),
            'files': (open(file_name, 'rb')),
        }
        response = session.post(mattermost_upload_url, files=upload_form_data)
        upload_file_ids.append(response.json()['file_infos'][0]['id'])

    post_data = {
        'channel_id': channel_id,
        'message': message,
        'file_ids': upload_file_ids
    }
    response = session.post(mattermost_post_url, data=json.dumps(post_data))


if __name__ == '__main__':
    main()
