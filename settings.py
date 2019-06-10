import os
import binascii


BASE_DIR = os.path.dirname(__file__)
LOAD_DAYS = 20
USE_MAGNET = False
SORT_TYPE = "torrentsDate" #rating
MIN_VOTES_KP = 500
MIN_VOTES_IMDB = 1500
HTML_SAVE_PATH = os.path.join(BASE_DIR,"releases.html")

TRANSMISSION_URL = 'http://192.168.0.80:9091/transmission/rpc/'

CONNECTION_ATTEMPTS = 3

RUTOR_BASE_URL = "http://rutor.info"
RUTOR_MONTHS = {"Янв": 1, "Фев": 2, "Мар": 3, "Апр": 4, "Май": 5, "Июн": 6, "Июл": 7, "Авг": 8, "Сен": 9, "Окт": 10, "Ноя": 11, "Дек": 12}
RUTOR_SEARCH_MAIN = "http://rutor.info/search/{}/{}/300/0/BDRemux|BDRip|(WEB%20DL)%201080p|2160p|1080%D1%80%7C2160%D1%80%7C1080i%20{}"

KINOPOISK_API_IOS_BASE_URL = "https://ma.kinopoisk.ru/ios/5.0.0/"
KINOPOISK_API_V1_BASE_URL = "https://ma.kinopoisk.ru"
KINOPOISK_API_IOS_FILMDETAIL = "getKPFilmDetailView?still_limit=9&filmID={}&uuid={}"
KINOPOISK_API_SALT = "IDATevHDS7"
KINOPOISK_CLIENTID = binascii.b2a_hex(os.urandom(12)).decode('ascii')
KINOPOISK_UUID = binascii.b2a_hex(os.urandom(16)).decode('ascii')
KINOPOISK_POSTER_URL = "https://st.kp.yandex.net/images/{}{}width=360"

KINOZAL_SEARCH_BDREMUX = "http://kinozal.tv/browse.php?s=%5E{}&g=3&c=0&v=4&d=0&w=0&t=0&f=0"
KINOZAL_SEARCH_BDRIP = "http://kinozal.tv/browse.php?s=%5E{}&g=3&c=0&v=3&d=0&w=0&t=0&f=0"
KINOZAL_USERNAME = ""
KINOZAL_PASSWORD = ""



