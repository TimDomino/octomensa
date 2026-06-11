class MenuItem:
    item_type = ""
    description = ""
    price = ""

    def __init__(self, item_type, description, price):
        self.item_type = item_type
        self.description = description
        self.price = price

    def __str__(self, compact=False):
        leader = ''
        if compact:
            leader = '- '

        if compact:
            return f'{leader}{self.description} | *{self.price}*\n'
        else:
            return f'**{self.item_type}**\n{leader}{self.description}\n*{self.price}*\n\n'
