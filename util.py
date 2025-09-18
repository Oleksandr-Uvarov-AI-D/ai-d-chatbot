import re
from dotenv import load_dotenv
import datetime
import json
from zoneinfo import ZoneInfo


load_dotenv()



def get_month_name(number, language):
    month_name = None

    if number == 1:
        if language == "en":
            month_name = "january"
        else:
            month_name =  "januari"
    elif number == 2:
        if language == "en":
            month_name = "february"
        else:
            month_name = "februari"
    elif number == 3:
        if language == "en":
            month_name = "march"
        else:
            month_name = "maart"
    elif number == 4:
        month_name = "april"
    elif number == 5:
        if language == "en":
            month_name = "may"
        else: 
            month_name = "mei"
    elif number == 6:
        if language == "en":
            month_name = "june"
        else:
            month_name = "juni"
    elif number == 7:
        if language == "en":
            month_name = "july"
        else:
            month_name = "juli"
    elif number == 8:
        if language == "en":
            month_name = "august"
        else:
            month_name = "augustus"
    elif number == 9:
        month_name = "september"
    elif number == 10:
        if language == "en":
            month_name = "october"
        else:
            month_name = "oktober"
    elif number == 11:
        month_name = "november"
    else:
        month_name = "december"


    # Using this because months are capitalized in English but not in Dutch
    if language == "en":
        return month_name.capitalize()
    return month_name



def get_today_date():
    return (datetime.datetime.now().strftime("%A"), datetime.datetime.now(ZoneInfo("Europe/Brussels")).strftime("%H:%M:%S"), datetime.date.today().isoformat())




# This method is used to make sure JSON is always extracted. 
# (Sometimes a chatbot replies with a text + JSON, so this eliminates errors by removing that redundant text)
def extract_json(s: str):
    if isinstance(s, dict):
        return s
    
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in string")
    
    json_str = s[start:end+1]
    return json.loads(json_str)


def remove_source(s: str):
    start = s.find("【")
    end = s.rfind("】")

    if start != -1 and end != -1:
        s = s[0:start] + s[end+1:]
    
    while True:
        if s[-1] == " " or s[-1] == "\n":
            s = s[:-1]
        else:
            break

    return s


def validate_email(email):
    """Return email if it's validated. Return False otherwise."""
    is_valid = bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email))

    if is_valid:
        return email
    return is_valid


def validate_phone(phone):
    """Return phone if it's validated. Return False otherwise."""
    if phone[0] == "+":
        phone_copy = phone[1:]
    else:
        phone_copy = phone

    try:
        phone_copy = int(phone_copy)
    except ValueError:
        return False
    return phone


