import os

# file paths
subscript_path = os.path.dirname(__file__)
screenshot_directory = os.path.join(subscript_path, '../output/')
download_site_dir = os.path.join(subscript_path, '../site')
download_site_name = 'mensa.html'

# settings related to data source
base_url = 'https://www.studierendenwerk-aachen.de/'
plan_url = 'speiseplaene/$(MENSA_NAME)-w$(LANG_MODIFIER).html'
additional_files = ['resources/css/view.css',
                    'resources/js/jquery.js', 'resources/js/script.js']
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
mattermost_post_url = os.path.join(mattermost_server_url, 'api/v4/posts')
mattermost_upload_url = os.path.join(mattermost_server_url, 'api/v4/files')
