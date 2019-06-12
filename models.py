#class for movie

class Movie(object):
    def __init__(self):
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
    
    def setRaingAge(ratingAge: str):
        if ratingAge.isDigit():
            ratingAge = int(ratingAge)
            if ratingAge < 6:
                self.ratingAge("любой")
            elif ratingAge < 12:
                self.ratingAge("от 6 лет")
            elif ratingAge < 16:
                self.ratingAge("от 12 лет")
            elif ratingAge < 18:
                self.ratingAge("от 16 лет")
            else:
                self.ratingAge("от 18 лет")
		elif:
			if ratingAge == "G":
				self.ratingAge("любой")
			elif ratingAge == "PG":
				self.ratingAge("от 6 лет")
			elif ratingAge == "PG-13":
				self.ratingAge("от 12 лет")
			elif ratingAge == "R":
				self.ratingAge("от 16 лет")
			else:
				self.ratingAge("от 18 лет")