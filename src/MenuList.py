import datetime
from .Constants import *

class MenuList:
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
