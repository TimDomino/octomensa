import datetime
from .Constants import *


class MenuList:
    """Class holding a list of MenuItem instances, overall representing the menu of a single day
    """

    date = datetime.datetime.today()
    menu_items = []

    def __init__(self, date):
        self.date = date
        self.menu_items = []

    def __str__(self, lang_shorthand, compact=False, colored=False):
        final_string = f'{weekdays[lang_shorthand][self.date.weekday()]}, {self.date.strftime(date_format)}\n'
        final_string += (len(final_string)+1) * '-' + '\n'

        for menu_item in self.menu_items:
            final_string += menu_item.__str__(compact, colored)

        return final_string
