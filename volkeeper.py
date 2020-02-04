#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests, json, sys
from requests.exceptions import ConnectionError

try:
    from config import *
except:
    print("Файл config.py не найден или заполнен некорректно.")
    exit(1)

if sys.version_info < (3,):
    def u(x):
        try:
            return x.encode("utf8")
        except UnicodeDecodeError:
            return x
else:
    def u(x):
        if type(x) == type(b''):
            return x.decode('utf8')
        else:
            return x

def direct_api_request(req, uri, params={}):
    if params == {}:
        print("Ошибка! Не заданы параметры запроса.")
        exit(0)
    campaignsURL = apiURL + uri
    clientLogin = ''
    headers = {"Authorization": "Bearer " + TOKEN,  # OAuth-токен. Использование слова Bearer обязательно
               "Client-Login": clientLogin,  # Логин клиента рекламного агентства
               "Accept-Language": "ru",  # Язык ответных сообщений
               }
    if req == 'get':
        body = {"method": "get",
                "params": params
                }
    elif req == 'set':
        body = {"method": "set",
                "params": params
                }
    else:
        print("Ошибка! неверно указан параметр get/set")
        exit(0)
    # Кодирование тела запроса в JSON
    jsonBody = json.dumps(body, ensure_ascii=False).encode('utf8')

    # Выполнение запроса
    try:
        result = requests.post(campaignsURL, jsonBody, headers=headers)

        # Отладочная информация
        # print("Заголовки запроса: ", u(result.request.headers))
        # print("Запрос: {}".format(u(result.request.body)))
        # print("Заголовки ответа: {}".format(result.headers))
        # print("Ответ: {}".format(u(result.text)))
        # print("\n")

        # Обработка запроса
        if result.status_code != 200 or result.json().get("error", False):
            print("Произошла ошибка при обращении к серверу API Директа.")
            print("Код ошибки: {}".format(result.json()["error"]["error_code"]))
            print("Описание ошибки: {}".format(u(result.json()["error"]["error_detail"])))
            print("RequestId: {}".format(result.headers.get("RequestId", False)))
        else:
            print("RequestId: {}".format(result.headers.get("RequestId", False)))
            print("Информация о баллах: {}".format(result.headers.get("Units", False)))
            # Вывод списка кампаний
            res = result.json()["result"]
            return res
            if res.get('limitedBy', False):
                print("Получены не все доступные объекты.")
                """Если ответ содержит параметр LimitedBy, значит,были получены не все доступные объекты.
                В этом случае следует выполнить дополнительные запросы для получения всех объектов. Не реализовано в данной версии.
                Подробное описание постраничной выборки https://tech.yandex.ru/direct/doc/dg/best-practice/get-docpage/#page"""

    # Обработка ошибки, если не удалось соединиться с сервером API Директа
    except ConnectionError:
        print("Произошла ошибка соединения с сервером API.")



def get_bids(id):  # Возвращает {KeywordId: AuctionBids}
        params = {"SelectionCriteria": {"CampaignIds": [id]},
                  "FieldNames": ["KeywordId"],
                  "SearchFieldNames": ["Bid", "AuctionBids"]
                  }
        try:
            out={}
            request_array = direct_api_request('get', 'keywordbids', params)['KeywordBids']
            for block in request_array:
                out[block["KeywordId"]] = block["Search"]
            return out
        except:
            print("Неверный ответ сервера. Завершение работы программы.")
            exit(1)


def set_search_bids_by_volume(new_bids_list):  # Устанавливаем новые ставки по всей кампании
    params = {"KeywordBids": new_bids_list}
    try:
        request_array = direct_api_request('set', 'keywordbids', params)
    except:
        print("Ошибка в функции set_search_bids_by_volume")
        exit(1)


def convert(x, a, b): # экстраполируем x из а[] в b[]
    """
    Если x точно попал на элемент из первого списка, возвращаем элемент второго списка под соответствующим номером.
    Если x в промежутке между двумя элементами первого списка, находим его относительную позицию между ними и
    значение между элементами второго списка, соответствующее этой относительной позиции.
    """
    for i in range(0, (len(a)-1)):
        if x == a[i]:
            return b[i]
        elif a[i] > x > a[i+1]:
                return int((x-a[i+1]) / (a[i]-a[i+1]) * (b[i]-b[i+1]) + b[i+1])
    return(b[0])


"""----------------------------------------------------------------------------------------------------------------"""
"""----------------------------------------------------------------------------------------------------------------"""

if __name__ == "__main__":
    print("________________________")
    print(" Volume Keeper Started ")
    print("------------------------")

    try: # Пытаемся получить аргументы
        target_volume, MAX_BID = int(sys.argv[1]), int(sys.argv[2])
        print("Устанавливаем объём трафика {0} для всех ключевых слов в \
кампании #{1}, но не более {2}р. за клик.".format(target_volume, campaignId, MAX_BID))
    except:
        print("ОШИБКА! Неверно указаны аргументы! \nvolkeeper.py [target_volume:int] [max_bid:int]\nПример: >python3 volkeeper.py 110 500")
        exit(1)
    # Поехали!
    data = get_bids(campaignId)
    bids_list = []
    new_bids_list = []
    # Для каждого Ключевого слова из data
    for keywordId in data:
        bids_list.append(data.get(keywordId)["Bid"])
        AuctionBidItems = data.get(keywordId)["AuctionBids"]["AuctionBidItems"]
        volume_list = [] # Обнуляем список доступных объемов, т.к. у разных ключевиков он почему-то отличается.
        bids_list = []
        prices_list = []
        # Перебор таблицы ставок для ключевого слова
        for i in range(0, len(AuctionBidItems)-1):
            volume_list.append(AuctionBidItems[i]["TrafficVolume"])
            bids_list.append(AuctionBidItems[i]["Bid"])
            prices_list.append(AuctionBidItems[i]["Price"])
        # Преобразовываем объем трафика в цену
        new_bid = convert(target_volume, volume_list, bids_list)
        # Сравниваем с максимальной
        if new_bid > MAX_BID * 1000000:
            new_bid = MAX_BID * 1000000

        new_bids_list.append({"KeywordId": keywordId, "SearchBid": new_bid})  # Добавляем в Список словари
    if new_bids_list != []: # Если колдунство удалось
        set_search_bids_by_volume(new_bids_list)
    else:
        print("Что-то пошло не так. Список новых ставок пуст.")
        exit(1)
    print("Старые ставки: ", bids_list)
    print("Новые ставки:", new_bids_list)
    print("\nНовые ставки успешно захуярены!")
