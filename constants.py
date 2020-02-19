from datetime import datetime

DRIVER_PATH = r'C:\Users\rape9001\Documents\chromedriver_win32\chromedriver.exe'
keywords = ['jezik', 'jezika', 'jeziku', 'jezikom', 'jezikov', 'jezikoma', 'jezikih', 'jeziki', 'jezike', 'jezični',
            'jezičen', 'jezičnega', 'jezičnemu', 'jezičnem', 'jezičnim', 'jezična', 'jezičnih', 'jezičnima',
            'jezične', 'jezičnimi', 'jezično', 'slovenščina', 'slovenščine', 'slovenščini', 'slovenščino',
            'slovenščini', 'slovenščin', 'slovenščinama', 'slovenščinah', 'slovenščinam', 'slovenščinami']

keywords_serbian = ['jezik', 'jezika', 'jeziku', 'jezikom', 'jezici', 'jezicima', 'jezike', 'jezički', 'jezičkog',
                    'jezičkoga', 'jezičkom', 'jezičkome', 'jezičkomu', 'jezičkim', 'jezičkima', 'jezičkih', 'jezičke',
                    'jezička', 'jezičkoj', 'jezičku', 'jezičko']

MIN_DATE = datetime.strptime("01.01.2015", '%d.%m.%Y')
MAX_DATE = datetime.strptime("01.01.2020", '%d.%m.%Y')

site_ids = {
    "Politika": "sr-01",
    "Delo": 'si-01',
    'Slovenske novice': 'si-02',
    'Dnevnik': 'si-03',
    'Večer': 'si-04',
    'Svet24': 'si-05',
    'ur24': 'si-06'
}

site_urls = {
    "Politika": "http://www.politika.rs/search/index/keyword:{}/sort:date/page:{}",
    "Delo": '',
    'Slovenske novice': '',
    'Dnevnik': '',
    'Večer': 'https://www.vecer.com/iskalnik?q={}&time_range={}&page={}',
    'Svet24': 'https://novice.svet24.si/iskanje?q={}&stran={}',
    'ur24': 'https://www.24ur.com/iskanje?q={}&stran={}'
}

FACEBOOK_COMMENTS_URL = 'https://www.facebook.com/plugins/feedback.php?app_id={}' \
                        '&channel=https://staticxx.facebook.com/connect/xd_arbiter.php?origin=https%3A%2F%2F{}' \
                        '&href={} '
site_comments = {
    "Politika": "http://www.politika.rs/api/v1/getComments/{}?page={}",
    "Delo": '',
    'Slovenske novice': '',
    'Dnevnik': '',
    'Večer': FACEBOOK_COMMENTS_URL,
    'Svet24': FACEBOOK_COMMENTS_URL,
    'ur24': 'https://gql.24ur.si/graphql/'
}
