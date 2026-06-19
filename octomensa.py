#!/bin/python
import datetime
import requests
import bs4
import json
import schedule
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

from src.Arguments import *
from src.MenuItem import MenuItem
from src.MenuList import MenuList
from src.Constants import *
from src.Utilities import *


def main():
    """Entry point of the application. Retrieves command line arguments and sets up the application in either daemon or one-time mode. 
    """

    arguments = parse_command_arguments()

    # run in daemon mode if argument provided
    if arguments.daemon_timestring:
        schedule.every().day.at(arguments.daemon_timestring).do(
            every_day, arguments=arguments)
        print(
            f'Running in daemon mode, retrieval every workday at {arguments.daemon_timestring}')

        while True:
            schedule.run_pending()
            time.sleep(5)

    # run only once if daemon argument is not provided
    else:
        retrive_and_output(arguments)


def every_day(arguments):
    """Callback function invoked every day at the specified time string when in daemon mode.

    Arguments:
    arguments -- the command line arguments given to the application

    Return arguments:
    (none)
    """

    today = datetime.datetime.today().replace(
        hour=0, minute=0, second=0, microsecond=0)
    print(f'Everyday callback started on {today.strftime("%A, %d/%m/%y")}')
    retrive_and_output(arguments)
    print('Everyday callback terminated')


def retrive_and_output(arguments):
    """Starting point to retrieve the required menus based on the provided arguments. Triggers the download of menus, potentially in multiple languages, merges the outputs, posts the results to the desired outlet. 

    Arguments:
    arguments -- the command line arguments given to the application

    Return arguments:
    (none)
    """

    # setup variables and directories
    if arguments.screenshot:
        prepare_output_directory(screenshot_directory)

    if arguments.lang == 'bi':
        languages_to_process = ['de', 'en']
    else:
        languages_to_process = [arguments.lang]

    if arguments.upload:
        mattermost_token = open(os.path.join(
            subscript_path, '../secret/mattermost-token.txt'), 'r').readline().replace('\n', '')

    # main part: iterate through languages and create desired results
    final_message = ''
    final_file_list = []
    for lang in languages_to_process:
        (message, file_list) = process_query_for_language(lang, arguments)
        final_message += message
        final_file_list = final_file_list + file_list

    # stich images together in bilingual mode
    if arguments.lang == 'bi' and arguments.screenshot:
        final_file_list = stitch_screenshots(final_file_list)

    # print or post results
    if arguments.upload:
        post_mattermost(mattermost_token, arguments.upload, final_message, final_file_list)
    elif len(final_message) > 0:
        print(final_message, end='')  # omits newline symbol


def process_query_for_language(lang, arguments):
    """Retrieves the mensa menu for a single language based on the specified arguments.

    Arguments:
    lang -- the language in which the menus should be retrieved (either 'en' or 'de')
    arguments -- the remaining command line arguments that specify the selection criteria

    Return arguments:
    message -- the text message output resulting from the query (empty when screenshot mode is defined)
    file list -- a list of files containing the screenshots resulting from the query (empty when text mode is defined)
    """

    sub_url = plan_url.replace(
        '$(MENSA_NAME)', mensa_names[arguments.mensa][0])
    sub_url = sub_url.replace(
        '$(LANG_MODIFIER)', lang_modifiers[lang])

    soup = download_current_menu_data(
        sub_url, arguments.vegetarian, arguments.vegan, arguments.color, arguments.lang == 'bi')
    menu_list = get_all_menus(soup)
    relative_list = get_relative_list(menu_list)
    print_list = get_print_list(
        relative_list, arguments.num_offset, arguments.num_past, arguments.num_future)

    # check if filter criteria yielded any result that should be output
    if print_list.count(True) > 0:

        # output screenshot if this mode is selected
        if arguments.screenshot:
            screenshot_list = take_screenshots(menu_list, relative_list,
                                               print_list, lang, screenshot_directory, arguments.mensa)
            return ('', screenshot_list)

        # output text by default
        else:
            print_string = print_relevant_menus(
                menu_list, print_list, lang, arguments.long, arguments.color)
            return (print_string, [])

    return ('', [])


def download_current_menu_data(suburl, vegetarian_only, vegan_only, color_highlight, add_row_padding):
    """Downloads the webpage containing the currently available menu data and filters it based on the provided parameters.

    Arguments:
    suburl -- the sub-URL pointing to the menu data of the desired location and language
    vegetarian_only -- boolean indicating to filter for vegetarian meals only
    vegan_only -- boolean indicating to filter for vegan meals only
    color_highlight -- boolean indicating to apply color highlighting for vegetarian and vegan meals on the webpage (relevant for screenshot mode)
    add_row_padding -- boolean indicating if all rows should be padded to have a height equal to two lines of dish description text (relevant for the alignment of dishes in bilingual screenshots with languages placed side-by-side)

    Return arguments:
    soup -- a BeautifulSoup object containing the downloaded and adjusted HTML source
    """

    # download additional files like css and js if they do not exist
    for filename in additional_files:
        if os.path.exists(os.path.join(download_site_dir, filename)):
            continue

        response = requests.get(os.path.join(base_url, filename))
        with open(os.path.join(download_site_dir, filename), 'wb+') as download_file:
            response.encoding = response.apparent_encoding
            download_file.write(response.text.encode('utf-8'))

    # download current plan
    response = requests.get(os.path.join(base_url, suburl))
    response.encoding = response.apparent_encoding

    if response.status_code == 200:
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        soup = filter_soup(soup, vegetarian_only, vegan_only)

        if color_highlight:
            soup = add_stylesheet_to_soup(soup, 'resources/css/custom_nutr_adjust.css')

        if add_row_padding:
            soup = add_stylesheet_to_soup(soup, 'resources/css/custom_table_height.css')

        with open(os.path.join(download_site_dir, download_site_name), 'wb') as download_file:
            download_file.write(str(soup).encode('utf-8'))

        return soup

    else:
        print(
            f'Error retrieving page. Response code is: {response.status_code}')
        sys.exit(1)


def filter_soup(soup, vegetarian_only, vegan_only):
    """Filters the downloaded HTML page of the menus for vegetarian or vegan meals only.

    Arguments:
    soup -- the BeautifulSoup object containing the downloaded HTML source
    vegetarian_only -- boolean indicating to filter for vegetarian meals only
    vegan_only -- boolean indicating to filter for vegan meals only

    Return arguments:
    soup -- a modified BeautifulSoup object with the desired filters applied
    """

    # return input if no filtering is required
    if not vegetarian_only and not vegan_only:
        return soup

    # when removing an element, flip odd even assignment for following items
    flip_odd_even = False

    for menu_row in soup.find_all('tr'):
        # other rows related to other stuff like side dishes can be skipped
        if not menu_row.has_attr('class'):
            continue

        # menus not matching the filter criteria can be removed
        if (vegan_only and 'vegan' not in menu_row['class']) \
                or (vegetarian_only and ('vegan' not in menu_row['class'] and 'OLV' not in menu_row['class'])):
            menu_row.decompose()
            flip_odd_even = not flip_odd_even
            continue

        # make sure menu of each day starts on odd row coloring, even after removals
        if menu_row.find_previous_sibling() == None:
            if 'even' in menu_row['class']:
                flip_odd_even = True
            else:
                flip_odd_even = False

        # perform the flip for the current row if required
        if flip_odd_even:
            if 'odd' in menu_row['class']:
                menu_row['class'].remove('odd')
                menu_row['class'].append('even')
            elif 'even' in menu_row['class']:
                menu_row['class'].remove('even')
                menu_row['class'].append('odd')

    return soup


def add_stylesheet_to_soup(soup, path):
    """Links another stylesheet to the downloaded HTML source.

    Arguments:
    soup -- the BeautifulSoup object containing the downloaded HTML source
    path -- the relative path to the stylesheet

    Return arguments:
    soup -- a modified BeautifulSoup object with the stylesheet added
    """

    head_tag = soup.find('head')
    link_tag = soup.new_tag('link', rel='stylesheet',
                            href=path)
    head_tag.append(link_tag)
    return soup


def get_all_menus(soup):
    """Parses the provided BeautifulSoup object for all available menus on the corresponding webpage.

    Arguments:
    soup -- the BeautifulSoup object containing the HTML source

    Return arguments:
    menus -- a list of MenuList objects for each day presented on the page of the soup object
    """

    menu_root_nodes = soup.find_all('div', 'preventBreak')
    menus = []

    for menu_root in menu_root_nodes:
        day_menu = get_day_menu(menu_root)
        menus.append(day_menu)

    return menus


def get_day_menu(menu_root_node):
    """Parses the provided DOM root node of a single day for all dishes available on that day.

    Arguments:
    menu_root_node -- the node of the original BeautifulSoup object referring to the requested day

    Return arguments:
    day_menu -- an instande of MenuList representing the dishes on that day
    """

    date_string = get_text_or_default(menu_root_node.find('a'))
    date_string = date_string.split(',')[1].lstrip()  # remove weekday
    datetime_object = datetime.datetime.strptime(date_string, date_format)
    day_menu = MenuList(datetime_object)

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
        menu_item = MenuItem(item_type, item_description,
                             item_price, vegetarian, vegan)
        day_menu.menu_items.append(menu_item)

    return day_menu


def get_text_or_default(html, default=""):
    """Gets the clean text out of the provided HTML tag by removing allergene letters and other undesired characters.

    Arguments:
    html -- the node from which the text should be extracted
    default -- the text to return when no text can be extracted

    Return arguments:
    return_string -- the retrieved string
    """

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
    """Takes a list of MenuList instances and computes their relative distance to today's date. 

    Arguments:
    menu_list -- the list of MenuList instances to create the relative list for

    Return arguments:
    relative_list -- a list of same length as menu_list, with each item containing an integer representing the distance to today's date. Today's menu refers to 0, the last menu before today to -1, the menu before that to -2, and so on. The next menu after today refers to 1, the menu after that to 2, and so on.
    """

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


def get_print_list(relative_list, num_offset, num_past, num_future):
    """Takes a relative list describing the available menus and computes a print list stating which of these menus match the desired filter criteria. 

    Arguments:
    relative_list -- a list of integers describing the distance of each menu to today's date, see get_relative_list()
    num_offset -- the number of entries to offset the calculation. An offset of 1, for example, takes the next menu in the future as the reference for the following parameters
    num_past -- the number of menus in the past from the reference menu to be included in the output. If num_offset is 0, the reference day is today.
    num_future -- the number of menus in the future from the reference menu to be included in the output. If num_offset is 0, the reference day is today.

    Return arguments:
    print_list -- a list of same length as relative_list, with each item containing a boolean stating whether the corresponding menu should be output based on the filter criteria.
    """

    print_list = [False for i in range(len(relative_list))]

    for i in range(len(relative_list)):
        if (relative_list[i] < num_offset and relative_list[i] >= -num_past+num_offset) or \
           (relative_list[i] > num_offset and relative_list[i] <= num_future+num_offset) or \
           (relative_list[i] == num_offset):

            print_list[i] = True

    return print_list


def print_relevant_menus(menu_list, print_list, lang_shorthand, long_output, colored):
    """Creates textual output describing the menus of interest by applying the print list from get_print_list() to the menu list from get_all_menus() 

    Arguments:
    menu_list -- a list of MenuList instances representing the downloaded menus
    print_list -- a list of booleans, same length as menu_list, with each boolean indicating whether the corresponding menu should be printed
    lang_shorthand -- the language to print the weekdays in, can be either 'en' or 'de'
    colored -- a boolean indicating if terminal colors should be used for the output

    Return arguments:
    output_print_string -- the resulting string of menus
    """

    output_print_string = ''

    for i in range(len(print_list)):
        if print_list[i]:
            output_print_string += menu_list[i].__str__(
                lang_shorthand=lang_shorthand, compact=not long_output, colored=colored) + '\n'

    return output_print_string


def take_screenshots(menu_list, relative_list, print_list, lang, output_dir, filename_prefix):
    """Creates screenshots of all menus of interest by applying the print list from get_print_list() to the menu list from get_all_menus()

    Arguments:
    menu_list -- a list of MenuList instances representing the downloaded menus
    relative_list -- a list of integers describing the distance of each menu to today's date, see get_relative_list()
    print_list -- a list of booleans, same length as menu_list, with each boolean indicating whether the corresponding menu should be printed
    lang -- a language indicator used in the filename of the output

    Return arguments:
    screenshot_list -- a list of filenames of the created screenshots
    """

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    browser = webdriver.Firefox(options=options)
    browser.get('file://' + os.path.join(download_site_dir, download_site_name))
    menu_accordion_items = browser.find_elements(
        By.CSS_SELECTOR, '.preventBreak')

    screenshot_list = []
    for i in range(len(print_list)):
        if print_list[i]:

            # if today is first screenshot, then do not click
            if not (len(screenshot_list) == 0 and relative_list[i] == 0):
                menu_accordion_items[i].click()
                time.sleep(1)

            file_name = f'{filename_prefix}-{menu_list[i].date.strftime("%Y-%m-%d")}-{lang}'
            file_path = f'{output_dir}/{file_name}.png'
            menu_accordion_items[i].screenshot(file_path)
            screenshot_list.append(file_path)

    browser.quit()
    return screenshot_list


def stitch_screenshots(screenshot_list):
    """In bilingual mode, stiches the german and the english menu screenshots together in one file by using imagemagick's montage tool.

    arguments:
    screenshot_list -- a list of screenshots created with take_screenshots(), where each filename ending with '-de' should have a corresponding file ending in '-en'

    return arguments:
    output_file_list -- a list of filenames of the stitched screenshot files
    """

    output_file_list = []

    for file_name in screenshot_list:
        if '-de.png' in file_name:
            second_file_name = file_name.replace('-de.png', '-en.png')
            stitched_file_name = file_name.replace('-de.png', '-bi.png')
            subprocess.run(['montage', file_name, second_file_name, '-tile', '2x1', '-geometry',
                           '+7+0', '-gravity', 'North', '-background', 'none', stitched_file_name])
            output_file_list.append(stitched_file_name)

    return output_file_list


def post_mattermost(token, channel_id, message, attachments=[]):
    """Posts the provided parameters to the configured Mattermost server.

    Arguments:
    token -- the access token to access the Mattermost server
    channel_id -- the ID of the Mattermost channel to post in
    message -- the text message to be posted
    attachments -- the files to be attached to the message (5 maximum)

    Return arguments:
    (none)
    """

    if len(attachments) > 5:  # terminate when too many attachments are provided
        print('Error: Upload of more than five attachments is not supported by Mattermost')
        sys.exit(1)
    elif len(attachments) == 0 and message == '':  # return when nothing to post
        return

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

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
