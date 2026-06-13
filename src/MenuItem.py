import termcolor

class MenuItem:
    """Class representing a single item on the menu of a particular day
    """

    item_type = ""
    description = ""
    price = ""
    vegetarian = False
    vegan = False

    def __init__(self, item_type, description, price, vegetarian, vegan):
        self.item_type = item_type
        self.description = description
        self.price = price
        self.vegetarian = vegetarian
        self.vegan = vegan

    def __str__(self, compact=False, colored=False):
        leader = ''
        if compact:
            leader = '- '

        if compact:
            out_string = f'{leader}{self.description} | *{self.price}*\n'
        else:
            out_string = f'**{self.item_type}**\n{leader}{self.description}\n*{self.price}*\n\n'

        if colored:
            if self.vegan:
                out_string = termcolor.colored(out_string, 'light_yellow')
            elif self.vegetarian:
                out_string = termcolor.colored(out_string, 'light_green')

        return out_string
