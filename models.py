# class for movie


class Movie(object):
    def __init__(self):
        self.rating_age = None
        self.torrentsDate = None
        self.rating = None
        self.torrentDate = None
        self.nameOriginal = None
        self.ratingStyle = None
        self.posterURL = None
        self.nameRU = None
        self.year = None
        self.country = None
        self.directors = None
        self.actors = None
        self.genre = None
        self.ratingAgeLimits = None
        self.filmLength = None
        self.webURL = None
        self.ratingKP = None
        self.ratingIMDb = None
        self.premierType = None
        self.filmID = None
        self.sortTorrentsDate = None
        self.description = None


    def set_rating_age(self, rating_age: str):
        if rating_age.isDigit():
            rating_age = int(rating_age)
            self.rating_age = self.take_digital_rating(rating_age)
        else:
            self.rating_age = self.take_pagi_rating(rating_age)

    @staticmethod
    def take_digital_rating(ratingAge):
        if ratingAge < 6:
            return "любой"
        elif ratingAge < 12:
            return "от 6 лет"
        elif ratingAge < 16:
            return "от 12 лет"
        elif ratingAge < 18:
            return "от 16 лет"
        return "от 18 лет"

    @staticmethod
    def take_pagi_rating(ratingAge):
        if ratingAge == "G":
            return "любой"
        elif ratingAge == "PG":
            return "от 6 лет"
        elif ratingAge == "PG-13":
            return "от 12 лет"
        elif ratingAge == "R":
            return "от 16 лет"
        return "от 18 лет"


class Torrent(object):
    def __init__(self, description_link, leechers, seeders, size, size_str):
        self.descriptionLink: str = description_link
        self.leechers: int = leechers
        self.seeders: int = seeders
        self.size: int = size
        self.sizeStr: str = size_str
