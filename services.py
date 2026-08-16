
import re, urllib.parse

def google_url(q):
    return "https://www.google.com/search?q="+urllib.parse.quote_plus(q)

def app_url(q):
    return "https://play.google.com/store/search?q="+urllib.parse.quote_plus(q)+"&c=apps"

def game_url(q):
    return "https://play.google.com/store/search?q="+urllib.parse.quote_plus(q)+"&c=games"

def youtube_url(q):
    return "https://www.youtube.com/results?search_query="+urllib.parse.quote_plus(q)

def love(a,b):
    import hashlib
    h=int(hashlib.sha256((str(a)+":"+str(b)).encode()).hexdigest()[:8],16)
    return h%101
