import requests
from util import get_month_name, extract_json
import os
from dotenv import load_dotenv
import json
from init_azure import make_message, run_agent, get_agents
from dateutil import parser
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo

load_dotenv()


CAL_API_KEY = os.getenv("CAL_API_KEY")
event_type_id = int(os.getenv("EVENT_TYPE_ID"))

# CAL_API_KEY = os.getenv("CAL_API_KEY_MIGUEL")
headers_event = {"Authorization": f"Bearer {CAL_API_KEY}"}
headers = {"cal-api-version": "2024-08-13",
            "Content-Type": "application/json",
              "Authorization": f"Bearer {CAL_API_KEY}"}

response = requests.get("https://api.cal.com/v2/event-types", headers=headers_event)
# event_type_id = int(os.getenv("EVENT_TYPE_ID_MIGUEL"))



agent_data, agent_summary, agent_summary_thread = get_agents()


def try_to_make_an_appointment(chatbot_message, thread_id):
    try: 
        if type(chatbot_message) != dict:
            message_json = extract_json(chatbot_message)
        else:
            message_json = chatbot_message["message"]

        if "name" not in message_json:
            return {"role": "assistant", "message": chatbot_message["message"], "thread_id": thread_id}
            
        name, email, phone_number= message_json["name"], message_json["email"], message_json["phone_number"]
        start, language, msg = message_json["start"], message_json["language"], message_json["message"]
        status_code = book_cal_event(name, email, phone_number, start, language)
        if status_code == 400:
            available_slots = get_days_and_times(event_type_id, start)
            if language == "en":
                msg = f"We are sorry, but this timeframe is not available. The closest timeframes available are {available_slots[0]} and {available_slots[1]}."
            else: 
                msg = f"Helaas is dit tijdsbestek niet beschikbaar. De dichtstbijzijnde tijdslots zijn {available_slots[0]} en {available_slots[1]}." 

        run = run_agent(agent_summary_thread.id, agent_summary.id)

        return {"role": "assistant", "message": msg, "thread_id": thread_id}
    except (ValueError, json.decoder.JSONDecodeError):
        return {"role": "assistant", "message": chatbot_message, "thread_id": thread_id}

def book_cal_event(name, email, phoneNumber, start, language="nl", tz="Europe/Brussels"):
    dt = parser.isoparse(start)
    dt = dt.replace(tzinfo=ZoneInfo(tz))

    start = str(dt).replace(" ", "T")
    payload = {
        "start": start,
        "attendee": {
            "name": name,
            "email": email,
            "timeZone": tz,
            "phoneNumber": phoneNumber,
            "language": language
        },
        "eventTypeId": event_type_id,
        "metadata": {"key": "value"}
    }
    response = requests.post(f"https://api.cal.com/v2/bookings", headers=headers, json=payload)

    print(response.json())
    status_code = response.status_code
    return status_code

def parse_date(input_date, time_zone):
    dt = parser.isoparse(input_date)
    dt = dt.replace(tzinfo=ZoneInfo(time_zone))

    return dt

def get_dates_in_timeframe(event_type_id, start, end, time_zone):
    params = {
        "eventTypeId": event_type_id,
        "start": start,
        "end": end,
        "timeZone": time_zone
    }

    response = requests.get("https://api.cal.com/v2/slots", headers={"cal-api-version": "2024-09-04"}, params=params)

    return response


def get_available_slots(event_type_id, target, start=None, end=None, tz="Europe/Brussels", language="nl"):
    dt = parse_date(target, tz)
    target = str(dt).replace(" ", "T")

    if start == None:
        one_month_before = dt - relativedelta(months=1)
        one_month_before_str = str(one_month_before).replace(" ", "T")

        start = one_month_before_str


    response_before_date = get_dates_in_timeframe(event_type_id, start, target, tz)


    if end == None:
        one_month_after = dt + relativedelta(months=1)
        one_month_after_str = str(one_month_after).replace(" ", "T")

        end = one_month_after_str


    response_after_date = get_dates_in_timeframe(event_type_id, target, end, tz)

    return (response_before_date, response_after_date, language)


def _extract_day_and_time_out_of_data(input_date, language):
    date, time =  input_date.split("T")
    month_number = int(date[5:7])
    month_name = get_month_name(month_number, language)
    day_number = int(date[8:10])
    formatted_time = time[:5]

    return day_number, month_name, formatted_time


def get_days_and_times(event_type_id, target, start=None, end=None, tz="Europe/Brussels", language="nl"):
    response_before_date, response_after_date, language = get_available_slots(event_type_id, target, start, end, tz, language)

    # Get the closest day available to the target (before the target time)
    if len(list(response_before_date.json()["data"])) != 0:
        latest_day_before_target = list(response_before_date.json()["data"])[-1]
        # The closest time to the target (before the target time)
        latest_time_before_target =  response_before_date.json()["data"][latest_day_before_target][-1]["start"]
        day_number_before, month_name_before, formatted_time_before = _extract_day_and_time_out_of_data(latest_time_before_target, language)

    
    days_test = list(response_before_date.json()["data"])
    time_test = response_before_date.json()["data"][latest_day_before_target][-1]["start"]


    # for the second date after, the earliest day may not be the same, so I need to check that.

    # Get the closest day available to the target (after the target time)
    earliest_day_after_target = list(response_after_date.json()["data"])[0]
    # The closest time to the target (after the target time)
    earliest_time_after_target = response_after_date.json()["data"][earliest_day_after_target][0]["start"]
    day_number_after, month_name_after, formatted_time_after = _extract_day_and_time_out_of_data(earliest_time_after_target, language)

    return (f"{day_number_before} {month_name_before}, {formatted_time_before}", f"{day_number_after} {month_name_after}, {formatted_time_after}")






# check if it works if there are no slots at all for the left (before) or maybe right (after) as well