import locale
from selenium import webdriver
import sqlite3
from sqlite3 import Error
import time
from selenium.common import NoSuchElementException
from datetime import datetime, timedelta
import unicodedata
import re
import random
import openpyxl

#для вывода дат на русском (например "ноября, декабря и тд")
locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))

# нормализуем кодировки
def normalize_text(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')

# удаляем эмоджи
def delete_emoji(text):
    regrex_pattern = re.compile(pattern = "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags = re.UNICODE)
    return regrex_pattern.sub(r'',text)

# поскольку часто в одном и том же описании объявления из раза в раз встречаются то кириллические символы, то латинница, притом в
# где-нибудь в середине текста, то есть например 'текст' написан как через кирилическую 'c', а в следующий раз встретится через латинскую
# поэтому лучшим выходом будет считать расстояние Левенштейна, а потом уже смотреть различия в процентом соотношении
def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def time_sleep():
    random_sleep_time = random.uniform(0.5, 1.5)
    time.sleep(random_sleep_time)

# разница в процентном соотношении между строками
def percentage_difference(s1, s2):
    distance = levenshtein_distance(s1, s2)
    max_length = max(len(s1), len(s2))
    return (distance / max_length) * 100
