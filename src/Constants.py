import os

subscript_path = os.path.dirname(__file__)

mensa_url = 'https://www.studierendenwerk-aachen.de/speiseplaene/$(MENSA_NAME)-w$(LANG_MODIFIER).html'
lang_modifiers = {'en': '-en', 'de': ''}

mattermost_post_url = 'https://mattermost.vr.rwth-aachen.de/api/v4/posts'
mattermost_upload_url = 'https://mattermost.vr.rwth-aachen.de/api/v4/files'
# mattermost_channel_id = '15tjecufht8s5mxcrt3u967cyy'  # Mensa channel
mattermost_channel_id = '44n1ysibmtbxme65pmhbwoofzy'  # Test channel
mattermost_token = open(os.path.join(
    subscript_path, '../secret/mattermost-token.txt'), 'r').readline().replace('\n', '')

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
screenshot_directory = os.path.join(subscript_path, '../output/')
