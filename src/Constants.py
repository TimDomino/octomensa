import os


# file paths
subscript_path = os.path.dirname(__file__)
screenshot_directory = os.path.join(subscript_path, '../output/')
download_site_path = os.path.join(subscript_path, '../site/mensa.html')

# settings related to data source
mensa_url = 'https://www.studierendenwerk-aachen.de/speiseplaene/$(MENSA_NAME)-w$(LANG_MODIFIER).html'
lang_modifiers = {'en': '-en', 'de': ''}
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

# settings related to Mattermost connection
mattermost_server_url = 'https://mattermost.vr.rwth-aachen.de/'
mattermost_post_url =   os.path.join(mattermost_server_url, 'api/v4/posts')
mattermost_upload_url = os.path.join(mattermost_server_url, 'api/v4/files')
mattermost_token = open(os.path.join(
    subscript_path, '../secret/mattermost-token.txt'), 'r').readline().replace('\n', '')
