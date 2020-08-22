import requests
from typing import Optional, Dict
from requests.exceptions import HTTPError


# FIXME: rewrite with async
def get_status(dept_id: int, uid: int)-> Optional[Dict]:
    url = f"http://info.midpass.ru/svc/pi/app_last/{dept_id}/{uid}"
    try:
        response = requests.get(url=url, verify=False)
    except HTTPError:
        return None
    return response.json()


def format_status(json_status: Dict)-> str:
    return f"Готов: {json_status['passportReady']} " \
        f"Статус: {json_status['originalApplicationInfo']['statusName']} " \
        f"Готовность: {json_status['originalApplicationInfo']['statusPercent']}"
