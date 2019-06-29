from bs4 import BeautifulSoup
import hashlib
import datetime
import urllib.request
from urllib.parse import urljoin
from urllib.parse import quote
import time
import gzip
import json
import html
import re
import operator
import os
import binascii
import urllib.parse
import http.cookiejar
import sys
from jinja2 import Template, Environment, FileSystemLoader

from models import Movie

from settings import (
    BASE_DIR, LOAD_DAYS, USE_MAGNET, SORT_TYPE, MIN_VOTES_KP, MIN_VOTES_IMDB, HTML_SAVE_PATH,
    CONNECTION_ATTEMPTS, RUTOR_BASE_URL, RUTOR_MONTHS, RUTOR_SEARCH_MAIN, KINOPOISK_API_IOS_BASE_URL,
    KINOPOISK_API_V1_BASE_URL, KINOPOISK_API_IOS_FILMDETAIL, KINOPOISK_API_SALT, KINOPOISK_CLIENTID,
    KINOPOISK_UUID, KINOPOISK_POSTER_URL, KINOZAL_SEARCH_BDREMUX, KINOZAL_SEARCH_BDRIP, KINOZAL_USERNAME,
    KINOZAL_PASSWORD, SOCKS5_IP
)

SOCKS5_PORT = 9050
if SOCKS5_IP:
    import socks
    from sockshandler import SocksiPyHandler


def start_create_release_page(load_days=LOAD_DAYS, for_render=False):
    print("Дата и время запуска программы: " + str(datetime.datetime.now()) + ".")
    print("Количество попыток при ошибках соединения: " + str(CONNECTION_ATTEMPTS) + ".")

    if SOCKS5_IP:
        print("Для rutor.info и kinozal.tv будет использоваться прокси-сервер SOCKS5: " + SOCKS5_IP + ":" + str(
            SOCKS5_PORT) + ".")

    print("Проверка доступности rutor.info...")
    try:
        content = loadRutorContent(RUTOR_SEARCH_MAIN.format(0, 0, ""), useProxy=True)
        count = rutorPagesCountForResults(content)
    except:
        print("Сайт rutor.info недоступен, или изменился его формат данных.")
        print("Работа программы принудительно завершена.")
        return 1
    else:
        print("Сайт rutor.info доступен.")

    print("Анализ раздач...")
    results = rutorResultsForDays(load_days)
    movies = convertRutorResults(results, load_days)
    movies.sort(key=operator.itemgetter("torrentsDate"), reverse=True)
    if for_render:
        return movies
    save_html(movies, HTML_SAVE_PATH)
    print("Работа программы завершена успешно.")

    return 0


def rutorResultsForDays(load_days):
    targetDate = datetime.date.today() - datetime.timedelta(days=load_days)
    groups = [1, 5, 7, 10]
    tmpSet = set()
    tmpResults = {}

    for group in groups:
        try:
            print("Загрузка списка предварительно подходящих раздач...")
            content = loadRutorContent(RUTOR_SEARCH_MAIN.format(0, group, ""), useProxy=True)
            count = rutorPagesCountForResults(content)
        except:
            raise ConnectionError(
                "Ошибка. Не удалось загрузить страницу с результатами поиска или формат данных rutor.info изменился.")

        i = 0
        needMore = True

        while needMore:
            pageResults = rutorResultsOnPage(content)
            for result in pageResults:
                if result["date"] >= targetDate:
                    element = parseRutorElement(result)
                    if not element:
                        continue
                    if (element["compareName"] in tmpSet):
                        continue
                    print("Обработка раздачи: {} ({})...".format(element["nameRU"], element["year"]))
                    try:
                        elements = rutorSearchSimilarElements(element, group)
                        elements = rutorFilmIDForElements(elements)
                    except:
                        raise ConnectionError(
                            "Ошибка. Не удалось загрузить данные похожих раздач или загрузить страницу с описанием.")
                    tmpSet.add(element["compareName"])
                    if len(elements) > 0:
                        if (tmpResults.get(elements[0]["filmID"])):
                            tmpResults[elements[0]["filmID"]].extend(elements)
                        else:
                            tmpResults[elements[0]["filmID"]] = elements
                else:
                    needMore = False
                    break
            i = i + 1
            if (i >= count):
                needMore = False
            if needMore:
                print("Загрузка списка предварительно подходящих раздач...")
                try:
                    content = loadRutorContent(RUTOR_SEARCH_MAIN.format(i, group, ""), useProxy=True)
                except:
                    raise ConnectionError(
                        "Ошибка. Не удалось загрузить страницу с результатами поиска или формат данных rutor.info изменился.")

    return tmpResults


def convertRutorResults(rutorResults, load_days):
    targetDate = datetime.date.today() - datetime.timedelta(days=load_days)
    minPremierDate = datetime.date.today() - datetime.timedelta(days=365)

    movies = []

    try:
        if KINOZAL_USERNAME:
            opener = kinozalAuth(KINOZAL_USERNAME, KINOZAL_PASSWORD)
        else:
            opener = None
    except:
        opener = None

    for key, values in rutorResults.items():
        BDDate = None
        WBDate = None
        for value in values:
            if "BD" in value["type"]:
                if not BDDate:
                    BDDate = value["date"]
                else:
                    BDDate = min(BDDate, value["date"])
            else:
                if not WBDate:
                    WBDate = value["date"]
                else:
                    WBDate = min(WBDate, value["date"])
        if BDDate:
            if BDDate < targetDate:
                continue
        else:
            if WBDate < targetDate:
                continue

        tr = {}

        for value in values:
            if value["type"] == "UHD BDRemux":
                if value["hdr"]:
                    if tr.get("UHD BDRemux HDR") != None:
                        if value["seeders"] > tr["UHD BDRemux HDR"]["seeders"]:
                            tr["UHD BDRemux HDR"] = value
                    else:
                        tr["UHD BDRemux HDR"] = value
                else:
                    if tr.get("UHD BDRemux SDR") != None:
                        if value["seeders"] > tr["UHD BDRemux SDR"]["seeders"]:
                            tr["UHD BDRemux SDR"] = value
                    else:
                        tr["UHD BDRemux SDR"] = value
            elif value["type"] == "BDRemux":
                if tr.get("BDRemux") != None:
                    if value["seeders"] > tr["BDRemux"]["seeders"]:
                        tr["BDRemux"] = value
                else:
                    tr["BDRemux"] = value
            elif value["type"] == "BDRip-HEVC":
                if tr.get("BDRip-HEVC 1080p") != None:
                    if value["seeders"] > tr["BDRip-HEVC 1080p"]["seeders"]:
                        tr["BDRip-HEVC 1080p"] = value
                else:
                    tr["BDRip-HEVC 1080p"] = value
            elif value["type"] == "BDRip":
                if tr.get("BDRip 1080p") != None:
                    if value["seeders"] > tr["BDRip 1080p"]["seeders"]:
                        tr["BDRip 1080p"] = value
                else:
                    tr["BDRip 1080p"] = value
            elif value["type"] == "WEB-DL":
                if value["resolution"] == "2160p":
                    if value["hdr"]:
                        if tr.get("WEB-DL 2160p HDR") != None:
                            if value["seeders"] > tr["WEB-DL 2160p HDR"]["seeders"]:
                                tr["WEB-DL 2160p HDR"] = value
                        else:
                            tr["WEB-DL 2160p HDR"] = value
                    else:
                        if tr.get("WEB-DL 2160p SDR") != None:
                            if value["seeders"] > tr["WEB-DL 2160p SDR"]["seeders"]:
                                tr["WEB-DL 2160p SDR"] = value
                        else:
                            tr["WEB-DL 2160p SDR"] = value
                else:
                    if tr.get("WEB-DL 1080p") != None:
                        if value["seeders"] > tr["WEB-DL 1080p"]["seeders"]:
                            tr["WEB-DL 1080p"] = value
                    else:
                        tr["WEB-DL 1080p"] = value

        if tr.get("UHD BDRemux HDR") or tr.get("UHD BDRemux SDR") or tr.get("BDRip-HEVC 1080p") or tr.get(
                "BDRip 1080p") or tr.get("BDRemux"):
            tr.pop("WEB-DL 2160p HDR", None)
            tr.pop("WEB-DL 2160p SDR", None)
            tr.pop("WEB-DL 1080p", None)

        if tr.get("UHD BDRemux HDR"):
            tr.pop("UHD BDRemux SDR", None)

        print("Загрузка данных для фильма с ID " + values[0]["filmID"] + "...")
        try:
            detail = filmDetail(values[0]["filmID"])
        except:
            print("Загрузка не удалась. Пропуск фильма с ID " + values[0]["filmID"] + ".")

        print("Загружены данные для фильма: " + detail["nameRU"] + ".")

        if not detail.get("premierDate"):
            print("У фильма \"" + detail["nameRU"] + "\" нет даты премьеры. Пропуск фильма.")
            continue
        if detail["premierDate"] < minPremierDate:
            print("Фильм \"" + detail["nameRU"] + "\" слишком старый. Пропуск фильма.")
            continue

        finalResult = []

        if tr.get("WEB-DL 1080p"):
            finalResult.append({"link": tr["WEB-DL 1080p"]["fileLink"], "magnet": tr["WEB-DL 1080p"]["magnetLink"],
                                "date": tr["WEB-DL 1080p"]["date"], "type": "WEB-DL 1080p"})
        if tr.get("WEB-DL 2160p HDR"):
            finalResult.append(
                {"link": tr["WEB-DL 2160p HDR"]["fileLink"], "magnet": tr["WEB-DL 2160p HDR"]["magnetLink"],
                 "date": tr["WEB-DL 2160p HDR"]["date"], "type": "WEB-DL 2160p HDR"})
        elif tr.get("WEB-DL 2160p SDR"):
            finalResult.append(
                {"link": tr["WEB-DL 2160p SDR"]["fileLink"], "magnet": tr["WEB-DL 2160p SDR"]["magnetLink"],
                 "date": tr["WEB-DL 2160p SDR"]["date"], "type": "WEB-DL 2160p SDR"})
        if tr.get("BDRip 1080p"):
            finalResult.append({"link": tr["BDRip 1080p"]["fileLink"], "magnet": tr["BDRip 1080p"]["magnetLink"],
                                "date": tr["BDRip 1080p"]["date"], "type": "BDRip 1080p"})
        elif (tr.get("BDRip-HEVC 1080p") or tr.get("BDRemux")) and opener:
            print("Пробуем найти отсутствующий BDRip 1080p на kinozal.tv...")
            kName = detail["nameRU"]
            kNameOriginal = detail["nameOriginal"]
            if not kNameOriginal:
                kNameOriginal = kName
            try:
                kRes = kinozalSearch({"nameRU": kName, "nameOriginal": kNameOriginal, "year": detail["year"]}, opener,
                                     "BDRip 1080p")
                if kRes:
                    print("Отсутствующий BDRip 1080p найден на kinozal.tv.")
                    finalResult.append(kRes)
            except:
                print(
                    "Какая-то ошибка при работе с kinozal.tv. Подробная информация о проблемах ещё не добавлена в функцию.")
        if tr.get("BDRip-HEVC 1080p"):
            finalResult.append(
                {"link": tr["BDRip-HEVC 1080p"]["fileLink"], "magnet": tr["BDRip-HEVC 1080p"]["magnetLink"],
                 "date": tr["BDRip-HEVC 1080p"]["date"], "type": "BDRip-HEVC 1080p"})
        elif (tr.get("BDRip 1080p") or tr.get("BDRemux")) and opener:
            print("Пробуем найти отсутствующий BDRip-HEVC 1080p на kinozal.tv...")
            kName = detail["nameRU"]
            kNameOriginal = detail["nameOriginal"]
            if not kNameOriginal:
                kNameOriginal = kName
            try:
                kRes = kinozalSearch({"nameRU": kName, "nameOriginal": kNameOriginal, "year": detail["year"]}, opener,
                                     "BDRip-HEVC 1080p")
                if kRes:
                    print("Отсутствующий BDRip-HEVC 1080p найден на kinozal.tv.")
                    finalResult.append(kRes)
            except:
                print(
                    "Какая-то ошибка при работе с kinozal.tv. Подробная информация о проблемах ещё не добавлена в функцию.")

        if tr.get("BDRemux"):
            finalResult.append({"link": tr["BDRemux"]["fileLink"], "magnet": tr["BDRemux"]["magnetLink"],
                                "date": tr["BDRemux"]["date"], "type": "BDRemux"})
        elif (tr.get("BDRip-HEVC 1080p") or tr.get("BDRip 1080p")) and opener:
            print("Пробуем найти отсутствующий BDRemux на kinozal.tv...")
            kName = detail["nameRU"]
            kNameOriginal = detail["nameOriginal"]
            if not kNameOriginal:
                kNameOriginal = kName
            try:
                kRes = kinozalSearch({"nameRU": kName, "nameOriginal": kNameOriginal, "year": detail["year"]}, opener,
                                     "BDRemux")
                if kRes:
                    print("Отсутствующий BDRemux найден на kinozal.tv.")
                    finalResult.append(kRes)
            except:
                print(
                    "Какая-то ошибка при работе с kinozal.tv. Подробная информация о проблемах ещё не добавлена в функцию.")
        if tr.get("UHD BDRemux HDR"):
            finalResult.append(
                {"link": tr["UHD BDRemux HDR"]["fileLink"], "magnet": tr["UHD BDRemux HDR"]["magnetLink"],
                 "date": tr["UHD BDRemux HDR"]["date"], "type": "UHD BDRemux HDR"})
        elif tr.get("UHD BDRemux SDR"):
            finalResult.append(
                {"link": tr["UHD BDRemux SDR"]["fileLink"], "magnet": tr["UHD BDRemux SDR"]["magnetLink"],
                 "date": tr["UHD BDRemux SDR"]["date"], "type": "UHD BDRemux SDR"})

        dates = []
        for torrent in finalResult:
            dates.append(torrent["date"])
        dates.sort()

        detail["torrents"] = finalResult
        detail["torrentsDate"] = dates[0]
        movies.append(detail)

    return movies


def loadRutorContent(URL, attempts=CONNECTION_ATTEMPTS, useProxy=False):
    headers = {}
    headers["Accept-encoding"] = "gzip"
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"

    return loadURLContent(URL, headers=headers, attempts=attempts, useProxy=useProxy)


def rutorPagesCountForResults(content):
    soup = BeautifulSoup(content, 'html.parser')

    if (not soup):
        raise ValueError("Ошибка. Невозможно инициализировать HTML-парсер, что-то не так с контентом.")

    try:
        resultsGroup = soup.find("div", id="index")
    except:
        raise ValueError("Ошибка. Нет блока с торрентами.")
    if not resultsGroup:
        raise ValueError("Ошибка. Нет блока с торрентами.")

    try:
        indexes = [text for text in resultsGroup.b.stripped_strings]
    except:
        raise ValueError("Ошибка. Нет блока со страницами результатов.")
    if len(indexes) == 0:
        raise ValueError("Ошибка. Нет блока со страницами результатов.")

    lastIndexStr = indexes[-1]
    if lastIndexStr.startswith("Страницы"):
        return 1

    lastIndex = int(lastIndexStr)

    if lastIndex <= 0:
        raise ValueError("Ошибка. Неверное значение индекса страницы.")

    return lastIndex


def loadURLContent(url, headers={}, attempts=CONNECTION_ATTEMPTS, useProxy=False):
    if useProxy and SOCKS5_IP:
        proxyHandler = SocksiPyHandler(socks.PROXY_TYPE_SOCKS5, SOCKS5_IP, SOCKS5_PORT)
        opener = urllib.request.build_opener(proxyHandler)
    else:
        opener = urllib.request.build_opener()

    request = urllib.request.Request(url, headers=headers)
    response = None
    n = attempts
    while n > 0:
        try:
            response = opener.open(request)
            break
        except:
            n = n - 1
            if (n <= 0):
                raise ConnectionError("Ошибка соединения. Все попытки соединения израсходованы.")

    if response.info().get("Content-Encoding") == "gzip":
        gzipFile = gzip.GzipFile(fileobj=response)
        content = gzipFile.read().decode("utf-8")
    else:
        content = response.read().decode("utf-8")

    return content


def kinopoiskRating(filmID, useProxy=False):
    result = {}

    headers = {}
    headers["Accept-encoding"] = "gzip"
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"

    if useProxy and SOCKS5_IP:
        proxyHandler = SocksiPyHandler(socks.PROXY_TYPE_SOCKS5, SOCKS5_IP, SOCKS5_PORT)
        opener = urllib.request.build_opener(proxyHandler)
    else:
        opener = urllib.request.build_opener()

    request = urllib.request.Request("https://rating.kinopoisk.ru/{}.xml".format(filmID), headers=headers)
    response = opener.open(request)
    if response.info().get("Content-Encoding") == "gzip":
        gzipFile = gzip.GzipFile(fileobj=response)
        content = gzipFile.read().decode(response.info().get_content_charset())
    else:
        content = response.read().decode(response.info().get_content_charset())

    patternKP = re.compile("<kp_rating num_vote=\"([0-9]+)\">([0-9]*\.[0-9]*)</kp_rating>")
    matches = re.findall(patternKP, content)

    if len(matches) == 1:
        result["rating"] = matches[0][1]
        result["ratingVoteCount"] = matches[0][0]

    patternIMDb = re.compile("<imdb_rating num_vote=\"([0-9]+)\">([0-9]*\.[0-9]*)</imdb_rating>")
    matches = re.findall(patternIMDb, content)

    if len(matches) == 1:
        result["ratingIMDb"] = matches[0][1]
        result["ratingIMDbVoteCount"] = matches[0][0]

    return result


def filmDetail(filmID):
    result = {}
    content = None

    try:
        content = loadKinopoiskContent(KINOPOISK_API_IOS_BASE_URL,
                                       KINOPOISK_API_IOS_FILMDETAIL.format(filmID, KINOPOISK_UUID))
    except:
        pass

    if content:
        tmpDict = json.loads(content)

        if tmpDict == None or not isinstance(tmpDict, dict):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Ответ не соответствует JSON.")
        if tmpDict.get("resultCode") != 0:
            raise ValueError(
                "Ошибка загрузки данных для filmID " + filmID + ". В ответе нет значения resultCode или оно не равно 0.")
        itemData = tmpDict.get("data")
        if itemData == None or not isinstance(itemData, dict):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением data.")
        nameRU = itemData.get("nameRU")
        if nameRU == None or not isinstance(nameRU, str):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением nameRU.")
        nameEN = itemData.get("nameEN")
        if nameEN == None or not isinstance(nameEN, str):
            nameEN = ""
        year = itemData.get("year")
        if year == None or not isinstance(year, str):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением year.")
        country = itemData.get("country")
        if country == None or not isinstance(country, str):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением country.")
        genre = itemData.get("genre")
        if genre == None or not isinstance(genre, str):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением genre.")
        description = itemData.get("description")
        if description == None or not isinstance(description, str):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением description.")
        ratingAgeLimits = itemData.get("ratingAgeLimits")
        if ratingAgeLimits == None or not isinstance(ratingAgeLimits, str):
            ratingAgeLimits = ""
        ratingMPAA = itemData.get("ratingMPAA")
        if ratingMPAA == None or not isinstance(ratingMPAA, str):
            ratingMPAA = ""
        posterURL = itemData.get("posterURL")
        if posterURL == None or not isinstance(posterURL, str):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением posterURL.")
        if "?" in posterURL:
            posterURL = KINOPOISK_POSTER_URL.format(posterURL, "&")
        else:
            posterURL = KINOPOISK_POSTER_URL.format(posterURL, "?")
        filmLength = itemData.get("filmLength")
        if filmLength == None or not isinstance(filmLength, str):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением filmLength.")
        ratingData = itemData.get("ratingData")
        if ratingData == None or not isinstance(ratingData, dict):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением ratingData.")
        ratingKP = ratingData.get("rating")
        if ratingKP == None or not isinstance(ratingKP, str):
            ratingKP = ""
        ratingKPCount = ratingData.get("ratingVoteCount")
        if ratingKPCount == None or not isinstance(ratingKPCount, str):
            ratingKPCount = "0"
        ratingKPCount = ratingKPCount.replace(" ", "")
        try:
            ratingKPCount = int(ratingKPCount)
        except:
            ratingKPCount = 0
        if ratingKPCount < MIN_VOTES_KP:
            ratingKP = ""
        ratingIMDb = ratingData.get("ratingIMDb")
        if ratingIMDb == None or not isinstance(ratingIMDb, str):
            ratingIMDb = ""
        ratingIMDbCount = ratingData.get("ratingIMDbVoteCount")
        if ratingIMDbCount == None or not isinstance(ratingIMDbCount, str):
            ratingIMDbCount = "0"
        ratingIMDbCount = ratingIMDbCount.replace(" ", "")
        try:
            ratingIMDbCount = int(ratingIMDbCount)
        except:
            ratingIMDbCount = 0
        if ratingIMDbCount < MIN_VOTES_IMDB:
            ratingIMDb = ""
        webURL = itemData.get("webURL")
        if webURL == None or not isinstance(webURL, str):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением webURL.")
        rentData = itemData.get("rentData")
        if rentData == None or not isinstance(rentData, dict):
            rentData = {}
        premiereRU = rentData.get("premiereRU")
        if not isinstance(premiereRU, str):
            premiereRU = None
        premiereWorld = rentData.get("premiereWorld")
        if not isinstance(premiereWorld, str):
            premiereWorld = None
        premiereDigital = rentData.get("premiereDigital")
        if not isinstance(premiereDigital, str):
            premiereDigital = None
        premierDate = None
        premierType = None
        if (not premierDate) and premiereRU:
            premierDate = datetime.datetime.strptime(premiereRU, "%d.%m.%Y").date()
            premierType = "ru"
        if (not premierDate) and premiereWorld:
            premierDate = datetime.datetime.strptime(premiereWorld, "%d.%m.%Y").date()
            premierType = "world"
        if (not premierDate) and premiereDigital:
            premierDate = datetime.datetime.strptime(premiereDigital, "%d.%m.%Y").date()
            premierType = "digital"

        directors = []
        actors = []

        creators = itemData.get("creators")
        if creators == None or not isinstance(creators, list):
            raise ValueError("Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением creators.")
        for personsGroup in creators:
            if not isinstance(personsGroup, list):
                raise ValueError(
                    "Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением creators > personsGroup.")
            for person in personsGroup:
                if not isinstance(person, dict):
                    raise ValueError(
                        "Ошибка загрузки данных для filmID " + filmID + ". Проблемы со значением creators > personsGroup > person.")
                if person.get("professionKey") == "director":
                    if person.get("nameRU"):
                        directors.append(person.get("nameRU"))
                if person.get("professionKey") == "actor":
                    if person.get("nameRU"):
                        actors.append(person.get("nameRU"))
    else:
        raise ValueError("Ошибка загрузки данных для filmID " + filmID + ".")

    freshRating = {}
    try:
        freshRating = kinopoiskRating(filmID)
    except:
        pass

    if freshRating.get("rating") and freshRating.get("ratingVoteCount"):
        ratingKP = freshRating.get("rating")
        ratingKPCount = freshRating.get("ratingVoteCount")
        try:
            ratingKP = "{0:.1f}".format(float(ratingKP))
            ratingKPCount = int(ratingKPCount)
        except:
            ratingKPCount = 0
        if ratingKPCount < MIN_VOTES_KP:
            ratingKP = ""

    if freshRating.get("ratingIMDb") and freshRating.get("ratingIMDbVoteCount"):
        ratingIMDb = freshRating.get("ratingIMDb")
        ratingIMDbCount = freshRating.get("ratingIMDbVoteCount")
        try:
            ratingIMDb = "{0:.1f}".format(float(ratingIMDb))
            ratingIMDbCount = int(ratingIMDbCount)
        except:
            ratingIMDbCount = 0
        if ratingIMDbCount < MIN_VOTES_IMDB:
            ratingIMDb = ""

    if ratingIMDb and ratingKP:
        rating = "{0:.1f}".format((float(ratingKP) + float(ratingIMDb)) / 2.0 + 0.001)
    elif ratingKP:
        rating = ratingKP
    elif ratingIMDb:
        rating = ratingIMDb
    else:
        rating = "0"

    directorsResult = ""
    if len(directors) > 0:
        for director in directors:
            directorsResult += director
            directorsResult += ", "
    if directorsResult.endswith(", "):
        directorsResult = directorsResult[:-2]

    actorsResult = ""
    if len(actors) > 0:
        for actor in actors:
            actorsResult += actor
            actorsResult += ", "
    if actorsResult.endswith(", "):
        actorsResult = actorsResult[:-2]

    result["filmID"] = filmID
    result["nameRU"] = nameRU
    result["nameOriginal"] = nameEN
    result["description"] = description
    result["year"] = year
    result["country"] = country
    result["genre"] = genre
    result["ratingAgeLimits"] = ratingAgeLimits
    result["ratingMPAA"] = ratingMPAA
    result["posterURL"] = posterURL
    result["filmLength"] = filmLength
    result["ratingKP"] = ratingKP
    result["ratingIMDb"] = ratingIMDb
    result["rating"] = rating
    result["ratingFloat"] = float(rating)
    result["directors"] = directorsResult
    result["actors"] = actorsResult
    result["webURL"] = webURL
    if premierDate:
        result["premierDate"] = premierDate
        result["premierType"] = premierType

    return result


def convertToAlfaNum(str):
    tmpStr = str.upper()
    tmpList = []
    for c in tmpStr:
        if c.isalnum():
            tmpList.append(c)
        else:
            tmpList.append(" ")

    return " ".join("".join(tmpList).split())


def replaceSimilarChars(str):
    tmpStr = str.upper()
    tmpStr = tmpStr.replace("A", "А")
    tmpStr = tmpStr.replace("B", "В")
    tmpStr = tmpStr.replace("C", "С")
    tmpStr = tmpStr.replace("E", "Е")
    tmpStr = tmpStr.replace("H", "Н")
    tmpStr = tmpStr.replace("K", "К")
    tmpStr = tmpStr.replace("M", "М")
    tmpStr = tmpStr.replace("O", "О")
    tmpStr = tmpStr.replace("P", "Р")
    tmpStr = tmpStr.replace("T", "Т")
    tmpStr = tmpStr.replace("X", "Х")
    tmpStr = tmpStr.replace("Y", "У")
    tmpStr = tmpStr.replace("Ё", "Е")

    return tmpStr


def parseRutorElement(dict):
    tmpParts = dict["name"].split("|")

    fullName = tmpParts[0].strip().upper()
    tags = set()
    tagsStr = ""

    if len(tmpParts) > 1:
        for i in range(1, len(tmpParts)):
            moreParts = tmpParts[i].split(",")
            for tmpPart in moreParts:
                tags.add(tmpPart.strip().upper())
                tagsStr = tagsStr + tmpPart.strip().upper() + " "

    if ("LINE" in tags) or ("UKR" in tags) or ("3D-VIDEO" in tags) or ("60 FPS" in tags) or (
            ("1080" in fullName) and ("HDR" in tags)) or ("UHD BDRIP" in fullName) or ("[" in fullName) or (
            "]" in fullName):
        return None

    patternYear = re.compile("\((\d{4})\)")
    match = re.search(patternYear, tmpParts[0])

    if not match:
        return None

    year = match.group(1)
    targetYear = (datetime.date.today() - datetime.timedelta(days=365)).year
    if int(year) < targetYear:
        return None

    namesPart = (tmpParts[0][:match.start()]).strip()
    typePart = (tmpParts[0][match.end():]).strip().upper()
    names = namesPart.split("/")
    RU = True if len(names) == 1 else False
    nameRU = names[0].strip()
    names.pop(0)
    if len(names) > 0:
        nameOriginal = names[-1]
    else:
        nameOriginal = nameRU

    if not RU:
        if not (("ЛИЦЕНЗИЯ" in tags) or ("ITUNES" in tags) or ("D" in tags) or ("D1" in tags) or ("D2" in tags) or (
                "НЕВАФИЛЬМ" in tags) or ("ПИФАГОР" in tags) or ("AMEDIA" in tags) or ("МОСФИЛЬМ-МАСТЕР" in tags) or (
                        "СВ-ДУБЛЬ" in tags) or ("КИРИЛЛИЦА" in tags) or ("АРК-ТВ" in tagsStr) or (
                        "APK-ТВ" in tagsStr) or ("APK-TB" in tagsStr)):
            return None

    if "UHD BDREMUX" in typePart:
        type = "UHD BDRemux"
    elif "BDREMUX" in typePart:
        type = "BDRemux"
    elif "BDRIP-HEVC" in typePart:
        type = "BDRip-HEVC"
    elif "BDRIP" in typePart:
        type = "BDRip"
    elif "WEB-DL " in typePart:
        type = "WEB-DL"
    elif "WEB-DL-HEVC" in typePart:
        # type = "WEB-DL-HEVC"
        type = "WEB-DL"
    else:
        return None

    hdr = False

    if "2160" in typePart:
        resolution = "2160p"
        hdr = True if ("HDR" in tags) else False
    elif "1080I" in typePart:
        resolution = "1080i"
    elif ("1080P" in typePart) or ("1080Р" in typePart):
        resolution = "1080p"
    else:
        return None

    IMAX = True if (("IMAX" in tags) or ("IMAX EDITION" in tags)) else False
    OpenMatte = True if ("OPEN MATTE" in tags) else False

    if RU:
        compareName = replaceSimilarChars(convertToAlfaNum(nameRU)) + " " + year
        searchPattern = "(^" + convertToAlfaNum(nameRU) + " " + year + ")|(^" + compareName + ")"
    else:
        compareName = replaceSimilarChars(convertToAlfaNum(nameRU)) + " " + convertToAlfaNum(nameOriginal) + " " + year
        searchPattern = "(^" + convertToAlfaNum(nameRU) + " " + convertToAlfaNum(
            nameOriginal) + " " + year + ")|(^" + compareName + ")"
        if len(searchPattern) > 130:
            searchPattern = "(^" + convertToAlfaNum(nameRU) + " " + convertToAlfaNum(nameOriginal) + " " + year + ")"

    result = {"date": dict["date"], "torrentName": dict["name"], "fileLink": dict["fileLink"],
              "magnetLink": dict["magnetLink"], "descriptionLink": dict["descriptionLink"], "size": dict["size"],
              "seeders": dict["seeders"], "leechers": dict["leechers"], "nameOriginal": nameOriginal, "nameRU": nameRU,
              "compareName": compareName, "searchPattern": searchPattern, "year": year, "type": type,
              "resolution": resolution, "hdr": hdr, "IMAX": IMAX, "OpenMatte": OpenMatte}

    return result


def rutorSearchSimilarElements(element, group):
    results = []
    content = loadRutorContent(RUTOR_SEARCH_MAIN.format(0, group, quote(element["searchPattern"])), useProxy=True)
    try:
        pageResults = rutorResultsOnPage(content)
    except:
        # print(RUTOR_SEARCH_MAIN.format(0, group, quote(element["searchPattern"])))
        return results

    for result in pageResults:
        tmpElement = parseRutorElement(result)
        if not tmpElement:
            continue
        if tmpElement["compareName"] == element["compareName"]:
            results.append(tmpElement)

    return results


def rutorResultsOnPage(content):
    soup = BeautifulSoup(content, 'html.parser')

    if (soup == None):
        raise ValueError("{} {}".format(datetime.datetime.now(),
                                        "Невозможно инициализировать HTML-парсер, что-то не так с контентом."))

    result = []
    try:
        resultsGroup = soup.find("div", id="index")
    except Exception:
        raise ValueError("{} {}".format(datetime.datetime.now(), "Нет блока с торрентами."))
    if resultsGroup == None:
        raise ValueError("{} {}".format(datetime.datetime.now(), "Нет блока с торрентами."))

    elements = resultsGroup.find_all("tr", class_=["gai", "tum"])

    if len(elements) == 0:
        return result

    for element in elements:
        film = parse_torrent(element)
        result.append(film)

    return result


def parse_torrent(element):
    allTDinElement = element.find_all("td", recursive=False)
    if len(allTDinElement) == 4:
        dateElement = allTDinElement[0]
        mainElement = allTDinElement[1]
        sizeElement = allTDinElement[2]
        peersElement = allTDinElement[3]
    elif len(allTDinElement) == 5:
        dateElement = allTDinElement[0]
        mainElement = allTDinElement[1]
        sizeElement = allTDinElement[3]
        peersElement = allTDinElement[4]
    else:
        raise ValueError("{} {}".format(datetime.datetime.now(), "Неверный формат блока торрента."))

    try:
        components = dateElement.string.split(u"\xa0")
        torrentDate = datetime.date(
            (int(components[2]) + 2000) if int(components[2]) < 2000 else int(components[2]),
            RUTOR_MONTHS[components[1]], int(components[0]))
    except Exception:
        raise ValueError("{} {}".format(datetime.datetime.now(), "Неверный формат блока даты."))

    try:
        seeders = int(peersElement.find("span", class_="green").get_text(strip=True))
        leechers = int(peersElement.find("span", class_="red").get_text(strip=True))
    except Exception:
        raise ValueError("{} {}".format(datetime.datetime.now(), "Неверный формат блока пиров."))

    try:
        sizeStr = sizeElement.get_text(strip=True)

        if sizeStr.endswith("GB"):
            multiplier = 1024 * 1024 * 1024
        elif sizeStr.endswith("MB"):
            multiplier = 1024 * 1024
        elif sizeStr.endswith("KB"):
            multiplier = 1024
        else:
            multiplier = 1

        components = sizeStr.split(u"\xa0")
        torrentSize = int(float(components[0]) * multiplier)
    except Exception:
        raise ValueError("{} {}".format(datetime.datetime.now(), "Неверный формат блока размера."))
    try:
        mainElements = mainElement.find_all("a")
        torrentFileLink = mainElements[0].get("href").strip()
        if not torrentFileLink.startswith("http"):
            torrentFileLink = urljoin("http://d.rutor.info", torrentFileLink)
        magnetLink = mainElements[1].get("href").strip()

        if not magnetLink.startswith("magnet"):
            raise ValueError("Magnet")

        torrentLink = quote(mainElements[2].get("href").strip())
        if not torrentLink.startswith("http"):
            torrentLink = urljoin(RUTOR_BASE_URL, torrentLink)

        torrentName = mainElements[2].get_text(strip=True)
    except Exception as e:
        raise ValueError(
            "{} {}".format(datetime.datetime.now(), "Неверный формат основного блока в блоке торрента."))

    return ({"date": torrentDate, "name": torrentName, "fileLink": torrentFileLink, "magnetLink": magnetLink,
             "descriptionLink": torrentLink, "size": torrentSize, "seeders": seeders, "leechers": leechers})


def rutorFilmIDForElements(elements):
    kID = None
    for element in elements:
        content = loadRutorContent(element["descriptionLink"], useProxy=True)

        patternLink = re.compile("\"http://www.kinopoisk.ru/film/(.*?)/\"")
        matches = re.findall(patternLink, content)
        if len(matches) == 1:
            kID = matches[0]
            break
        elif len(matches) > 1:
            return []

        if not kID:
            patternLink = re.compile("\"http://www.kinopoisk.ru/level/1/film/(.*?)/\"")
            matches = re.findall(patternLink, content)
            if len(matches) == 1:
                kID = matches[0]
                break
            elif len(matches) > 1:
                return []

    if kID:
        for element in elements:
            element["filmID"] = kID
    else:
        return []

    return elements


def loadKinopoiskContent(baseURL, requestMethod, CLIENTID=KINOPOISK_CLIENTID, API_SALT=KINOPOISK_API_SALT,
                         attempts=CONNECTION_ATTEMPTS, useProxy=False):
    timestamp = str(int(round(time.time() * 1000)))
    hashString = requestMethod + timestamp + API_SALT

    headers = {}
    headers["Accept-encoding"] = "gzip"
    headers["Accept"] = "application/json"
    headers["User-Agent"] = "Android client (6.0.1 / api23), ru.kinopoisk/4.6.5 (86)"
    headers["Image-Scale"] = "3"
    headers["device"] = "android"
    headers["ClientId"] = CLIENTID
    headers["countryID"] = "2"
    headers["cityID"] = "1"
    headers["Android-Api-Version"] = "23"
    headers["clientDate"] = datetime.date.today().strftime("%H:%M %d.%m.%Y")
    headers["device"] = "android"
    headers["X-TIMESTAMP"] = timestamp
    headers["X-SIGNATURE"] = hashlib.md5(hashString.encode('utf-8')).hexdigest()

    return loadURLContent(baseURL + requestMethod, headers=headers, attempts=attempts, useProxy=useProxy)


def kinozalAuth(username, password, useProxy=True):
    headers = {}
    headers["Accept-encoding"] = "gzip"
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"

    cookiejar = http.cookiejar.CookieJar()

    if useProxy and SOCKS5_IP:
        proxyHandler = SocksiPyHandler(socks.PROXY_TYPE_SOCKS5, SOCKS5_IP, SOCKS5_PORT)
        opener = urllib.request.build_opener(proxyHandler)
        opener.add_handler(urllib.request.HTTPCookieProcessor(cookiejar))
    else:
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar))

    values = {"username": username, "password": password}
    data = urllib.parse.urlencode(values).encode()

    request = urllib.request.Request("http://kinozal.tv/takelogin.php", data=data, headers=headers)
    _ = opener.open(request)
    cookieSet = set()

    for cookie in cookiejar:
        cookieSet.add(cookie.name)

    if ("pass" in cookieSet) and ("uid" in cookieSet):
        return opener

    return None


def kinozalSearch(filmDetail, opener, type):
    targetDate = datetime.date.today() - datetime.timedelta(days=LOAD_DAYS)
    headers = {}
    headers["Accept-encoding"] = "gzip"
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"

    _ = {}
    DBResults = []
    PMResults = []

    if type == "BDRip 1080p" or type == "BDRip-HEVC 1080p":
        request = urllib.request.Request(KINOZAL_SEARCH_BDRIP.format(quote(filmDetail["nameRU"])), headers=headers)
    elif type == "BDRemux":
        request = urllib.request.Request(KINOZAL_SEARCH_BDREMUX.format(quote(filmDetail["nameRU"])), headers=headers)
    else:
        return None

    response = opener.open(request)
    if response.info().get("Content-Encoding") == "gzip":
        gzipFile = gzip.GzipFile(fileobj=response)
        content = gzipFile.read().decode(response.info().get_content_charset())
    else:
        content = response.read().decode(response.info().get_content_charset())

    content = content.replace("\n", "")
    soup = BeautifulSoup(content, 'html.parser')

    elements = soup.find_all("td", class_=["nam"])

    if len(elements) == 0:
        return None

    for element in elements:
        contents = element.contents
        if len(contents) != 7:
            continue

        fullName = contents[0].get_text(strip=True)
        torrentLink = contents[0].get("href").strip()
        seeders = int(contents[3].get_text(strip=True))
        leechers = int(contents[4].get_text(strip=True))
        dateStr = contents[5].get_text(strip=True)

        if "сегодня" in dateStr:
            torrentDate = datetime.date.today()
        elif "вчера" in dateStr:
            torrentDate = datetime.date.today() - datetime.timedelta(days=1)
        else:
            patternDate = re.compile("\d{2}.\d{2}.\d{4}")
            matches = re.findall(patternDate, dateStr)
            if len(matches) != 1:
                continue
            torrentDate = datetime.datetime.strptime(matches[0], "%d.%m.%Y").date()

        if torrentDate <= targetDate:
            continue

        patternID = re.compile("id=(\d+)")
        matches = re.findall(patternID, torrentLink)
        if len(matches) != 1:
            continue
        kinozalID = matches[0]

        patternYear = re.compile("/ \d{4} /")
        match = re.search(patternYear, fullName)

        if not match:
            continue

        namesPart = (fullName[:match.end()]).strip().upper().replace("Ё", "Е")
        typePart = (fullName[match.end():]).strip().upper()

        year = int(filmDetail["year"])
        nameRU = filmDetail["nameRU"].upper().replace("Ё", "Е")
        nameOriginal = filmDetail["nameOriginal"].upper().replace("Ё", "Е")

        if type == "BDRip 1080p":
            if not ((nameRU in namesPart) and (nameOriginal in namesPart) and (
                    (str(year) in namesPart) or (str(year - 1) in namesPart) or (str(year + 1) in namesPart)) and (
                            "BDRIP" in typePart) and ("1080P" in typePart)):
                continue
            if ("HEVC" in typePart):
                continue
        elif type == "BDRemux":
            if not ((nameRU in namesPart) and (nameOriginal in namesPart) and (
                    (str(year) in namesPart) or (str(year - 1) in namesPart) or (str(year + 1) in namesPart)) and (
                            "REMUX" in typePart) and (("1080P" in typePart) or ("1080I" in typePart))):
                continue
        elif type == "BDRip-HEVC 1080p":
            if not ((nameRU in namesPart) and (nameOriginal in namesPart) and (
                    (str(year) in namesPart) or (str(year - 1) in namesPart) or (str(year + 1) in namesPart)) and (
                            "BDRIP" in typePart) and ("HEVC" in typePart) and ("1080P" in typePart)):
                continue
        else:
            return None

        if ("3D" in typePart) or ("TS" in typePart) or ("LINE" in typePart):
            continue

        if ("ДБ" in typePart) or ("РУ" in typePart):
            DBResults.append(
                {"fullName": fullName, "kinozalID": kinozalID, "torrentDate": torrentDate, "seeders": seeders,
                 "leechers": leechers})

        if ("ПМ" in typePart) and not (("ДБ" in typePart) or ("РУ" in typePart)):
            PMResults.append(
                {"fullName": fullName, "kinozalID": kinozalID, "torrentDate": torrentDate, "seeders": seeders,
                 "leechers": leechers})

    if len(DBResults) > 0:
        DBResults.sort(key=operator.itemgetter("seeders"), reverse=True)
        if DBResults[0]["seeders"] == 0:
            # return None
            DBResults.sort(key=operator.itemgetter("torrentDate"), reverse=True)
        request = urllib.request.Request(
            "http://kinozal.tv/get_srv_details.php?id={}&action=2".format(DBResults[0]["kinozalID"]), headers=headers)
        response = opener.open(request)
        if response.info().get("Content-Encoding") == "gzip":
            gzipFile = gzip.GzipFile(fileobj=response)
            content = gzipFile.read().decode(response.info().get_content_charset())
        else:
            content = response.read().decode(response.info().get_content_charset())

        patternHash = re.compile("[A-F0-9]{40}")
        match = re.search(patternHash, content)

        if not match:
            return None

        return {"link": "http://dl.kinozal.tv/download.php?id={}".format(DBResults[0]["kinozalID"]),
                "magnet": "magnet:?xt=urn:btih:{}&dn=kinozal.tv".format(match.group(0)),
                "date": DBResults[0]["torrentDate"],
                "type": type}
    elif len(PMResults) > 0:
        newPMResults = []

        for pm in PMResults:
            request = urllib.request.Request("http://kinozal.tv/details.php?id={}".format(PMResults[0]["kinozalID"]),
                                             headers=headers)
            response = opener.open(request)
            if response.info().get("Content-Encoding") == "gzip":
                gzipFile = gzip.GzipFile(fileobj=response)
                content = gzipFile.read().decode(response.info().get_content_charset())
            else:
                content = response.read().decode(response.info().get_content_charset())
            patternTabID = re.compile("<a onclick=\"showtab\({},(\d)\); return false;\" href=\"#\">Релиз</a>".format(
                PMResults[0]["kinozalID"]))
            matches = re.findall(patternTabID, content)
            if len(matches) != 1:
                continue

            request = urllib.request.Request(
                "http://kinozal.tv/get_srv_details.php?id={}&pagesd={}".format(PMResults[0]["kinozalID"], matches[0]),
                headers=headers)
            response = opener.open(request)
            if response.info().get("Content-Encoding") == "gzip":
                gzipFile = gzip.GzipFile(fileobj=response)
                content = gzipFile.read().decode(response.info().get_content_charset())
            else:
                content = response.read().decode(response.info().get_content_charset())

            content = content.upper()
            if ("ЛИЦЕНЗИЯ" in content) or ("ITUNES" in content) or ("НЕВАФИЛЬМ" in content) or (
                    "ПИФАГОР" in content) or ("AMEDIA" in content) or ("МОСФИЛЬМ-МАСТЕР" in content) or (
                    "СВ-ДУБЛЬ" in content) or ("АРК-ТВ" in content) or ("APK-ТВ" in content) or (
                    "APK-TB" in content) or ("КИРИЛЛИЦА" in content):
                newPMResults.append(pm)

        if len(newPMResults) > 0:
            newPMResults.sort(key=operator.itemgetter("seeders"), reverse=True)
            if newPMResults[0]["seeders"] == 0:
                # return None
                newPMResults.sort(key=operator.itemgetter("torrentDate"), reverse=True)
            request = urllib.request.Request(
                "http://kinozal.tv/get_srv_details.php?id={}&action=2".format(newPMResults[0]["kinozalID"]),
                headers=headers)
            response = opener.open(request)
            if response.info().get("Content-Encoding") == "gzip":
                gzipFile = gzip.GzipFile(fileobj=response)
                content = gzipFile.read().decode(response.info().get_content_charset())
            else:
                content = response.read().decode(response.info().get_content_charset())

            patternHash = re.compile("[A-F0-9]{40}")
            match = re.search(patternHash, content)

            if not match:
                return None

            return {"link": "http://dl.kinozal.tv/download.php?id={}".format(newPMResults[0]["kinozalID"]),
                    "magnet": "magnet:?xt=urn:btih:{}&dn=kinozal.tv".format(match.group(0)),
                    "date": newPMResults[0]["torrentDate"], "type": type}
    return None


def save_html(movies, filePath, useMagnet=USE_MAGNET):
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('template.html')
    ready_html = template.render(movies=movies)
    with open(filePath, 'w') as f:
        f.write(ready_html)
    return ready_html

if __name__ == "__main__":
    try:
        exitCode = start_create_release_page()
    except Exception as e:
        exitCode = str(e)

    sys.exit(exitCode)
