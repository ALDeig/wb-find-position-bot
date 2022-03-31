import asyncio
from collections import namedtuple
from json.decoder import JSONDecodeError
from random import choice

import httpx

from tgbot.services.errors import BadRequestInWB, ErrorInWBService


USER_AGENT_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
]

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    'user-agent': USER_AGENT_LIST[3]
}

PARAMS = {
    'spp': '0',
    'regions': '75,64,4,38,30,33,70,66,40,71,22,31,68,80,69,48,1',
    'stores': '119261,122252,122256,117673,122258,122259,121631,122466,122467,122495,122496,122498,122590,122591,\
122592,123816,123817,123818,123820,123821,123822,124093,124094,124095,124096,124097,124098,124099,124100,124101,124583,\
124584,125238,125239,125240,132318,132320,132321,125611,133917,132871,132870,132869,132829,133084,133618,132994,133348,\
133347,132709,132597,132807,132291,132012,126674,126676,127466,126679,126680,127014,126675,126670,126667,125186,116433,\
119400,507,3158,117501,120602,6158,121709,120762,124731,1699,130744,2737,117986,1733,686,132043',
    'pricemarginCoeff': '1.0',
    'reg': '0',
    'appType': '1',
    'offlineBonus': '0',
    'onlineBonus': '0',
    'emp': '0',
    'locale': 'ru',
    'lang': 'ru',
    'curr': 'rub',
    'couponsGeo': '12,3,18,15,21',
    'xsearch': 'true',
}

PARAMS_URL = "https://wbxsearch.wildberries.ru/exactmatch/v2/common"
SEARCH_URL = "https://wbxcatalog-ru.wildberries.ru/{category}/catalog"
TIMEOUT = 20


parsed_message = namedtuple("parsed_message", "scu, query")


def parse_message(msg) -> parsed_message | None:
    msg = msg.split()
    if len(msg) < 2 or not msg[0].isdigit():
        return
    return parsed_message(scu=int(msg[0]), query=" ".join(msg[1:]))


async def _get_params_query(client: httpx.AsyncClient, query: str) -> dict:
    query = "+".join(query.split()).lower()
    params = {"query": query}
    try:
        response = await client.get(PARAMS_URL, params=params)
    except httpx.TimeoutException:
        raise BadRequestInWB
    try:
        result = response.json()
        if not result:
            raise BadRequestInWB
        return result
    except JSONDecodeError:
        raise BadRequestInWB


async def _get_data_for_search_query(client: httpx.AsyncClient, got_params: dict, query_search: str, page: int):
    queries = got_params.get("query").split("&")
    params = PARAMS.copy()
    params.update({
        "xfilters": got_params.get("filters"),
        "xparams": got_params.get("query"),
        "xshard": got_params.get("shardKey"),
        "search": query_search,
        "page": page
    })
    for query in queries:
        query = query.split("=")
        params[query[0]] = query[-1]
    try:
        response = await client.get(SEARCH_URL.format(category=got_params.get("shardKey")), params=params)
    except httpx.TimeoutException:
        raise ErrorInWBService
    try:
        return response.json()
    except JSONDecodeError:
        raise ErrorInWBService


async def get_list_product_id(client: httpx.AsyncClient, params: dict, search_query: str, page: int) -> list[int]:
    try:
        data = await _get_data_for_search_query(client, params, search_query, page)
    except ErrorInWBService:
        return []
    product_id_list = [product["id"] for product in data["data"]["products"]]
    return product_id_list


def find_position_in_list(list_scu: list, scu: int) -> int | None:
    try:
        index_scu = list_scu.index(scu)
        return index_scu + 1
    except ValueError:
        return


async def find_position(search_query: str, scu: int) -> tuple:
    headers = {
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        'user-agent': choice(USER_AGENT_LIST)
    }
    async with httpx.AsyncClient(headers=headers, timeout=TIMEOUT) as client:
        params = await _get_params_query(client, search_query)
        for page in range(1, 101):
            list_product_id = await get_list_product_id(client, params, search_query, page)
            if not list_product_id:
                return False, page - 1
            index_scu = find_position_in_list(list_product_id, scu)
            if index_scu:
                return index_scu, page
            await asyncio.sleep(0.3)
        return False, 100

