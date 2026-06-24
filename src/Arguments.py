import argparse
from .Constants import mensa_names


def parse_command_arguments():
    """Sets up the argparse module and parses all arguments from the command line

    Arguments:
    (none)

    Return arguments:
    arguments -- a list of arguments provided to the application as given by argparse
    """

    list_of_mensas = 'Available locations are '
    for key in mensa_names.keys():
        list_of_mensas += f'{mensa_names[key][1]} ({key}), '
    list_of_mensas = list_of_mensas[:-2]

    parser = argparse.ArgumentParser(
        prog='octomensa.py',
        description="OctoMensa: Your favorite command-line tool for finding out what's on the menu at all of Aachen's " \
                    "finest dining places",
        epilog=list_of_mensas)
    parser.add_argument('-m', '--mensa', help="the mensa to retrieve the menu for, default is 'vita'",
                        choices=mensa_names.keys(), default=list(mensa_names.keys())[0])
    parser.add_argument('-p', '--past', type=int, help="print previous NUM_PAST menus, default is all",
                        nargs='?', const=20, default=0, dest='num_past')
    parser.add_argument('-f', '--future', type=int, help="print next NUM_FUTURE menus, default is all",
                        nargs='?', const=20, default=0, dest='num_future')
    parser.add_argument('-o', '--offset', type=int, help="offset the output by NUM_OFFSET menus, default is 0",
                        default=0, dest='num_offset')
    parser.add_argument('-v', '--vegetarian', action='store_true',
                        help="only show vegetarian options")
    parser.add_argument('-vv', '--vegan', action='store_true',
                        help="only show vegan options")
    parser.add_argument('-l', '--long', action='store_true',
                        help="use long instead of compact output, including dish category")
    parser.add_argument('-c', '--color', action='store_true',
                        help="use colored output, default is false")
    parser.add_argument('-lg', '--lang', help="select the language to retrieve, default is 'en'",
                        choices=['en', 'de', 'bi'], default='en')
    parser.add_argument('-s', '--screenshot', action='store_true',
                        help="save a screenshot of each selected menu")
    parser.add_argument('-u', '--upload', action='store',
                        help="upload the result to Mattermost, takes the channel ID as parameter")
    parser.add_argument('-d', '--daemon', action='store',
                        help='run as daemon to retrieve plan every day at the given clock time string, e.g., 08:00', dest='daemon_timestring')

    return parser.parse_args()
