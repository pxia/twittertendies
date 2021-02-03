#!/usr/bin/env python3

import time
import requests
import os
import json
import re
import telegram
import markdown_strings
import secrets

FOLLOWS = [
    "PJ_Matlock",
    "garyblack00",
    "CitronResearch",
    "anandchokkavelu",
    "OphirGottlieb",
    "Beth_Kindig",
]


def create_headers(bearer_token):
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers


class Updater:
    def __init__(self, telegram_bot):
        self.telegram_bot = telegram_bot
        self.ticker_pattern = re.compile("\$[A-Za-z]{2,5}")

    def get_rules(self, headers, bearer_token):
        response = requests.get(
            "https://api.twitter.com/2/tweets/search/stream/rules", headers=headers
        )
        if response.status_code != 200:
            raise Exception(
                "Cannot get rules (HTTP {}): {}".format(
                    response.status_code, response.text
                )
            )
        print(json.dumps(response.json()))
        return response.json()

    def delete_all_rules(self, headers, bearer_token, rules):
        if rules is None or "data" not in rules:
            return None

        ids = list(map(lambda rule: rule["id"], rules["data"]))
        payload = {"delete": {"ids": ids}}
        response = requests.post(
            "https://api.twitter.com/2/tweets/search/stream/rules",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            raise Exception(
                "Cannot delete rules (HTTP {}): {}".format(
                    response.status_code, response.text
                )
            )
        print(json.dumps(response.json()))

    def set_rules(self, headers, bearer_token):
        # You can adjust the rules if needed
        sample_rules = list(
            map(lambda user: {"value": "from:" + user, "tag": user}, FOLLOWS)
        )
        sample_rules.append({"value": "from:peterxia_com", "tag": "peterxia_com"})
        payload = {"add": sample_rules}
        response = requests.post(
            "https://api.twitter.com/2/tweets/search/stream/rules",
            headers=headers,
            json=payload,
        )
        if response.status_code != 201:
            raise Exception(
                "Cannot add rules (HTTP {}): {}".format(
                    response.status_code, response.text
                )
            )
        print(json.dumps(response.json()))

    def get_stream(self, headers, set, bearer_token):
        for i in range(5):
            response = requests.get(
                "https://api.twitter.com/2/tweets/search/stream",
                headers=headers,
                stream=True,
            )
            print(response.status_code)
            if response.status_code == 200:
                break
            elif response.status_code == 429:
                time.sleep(10)
                continue
            else:
                raise Exception(
                    "Cannot get stream (HTTP {}): {}".format(
                        response.status_code, response.text
                    )
                )

        print("!!!-----stream started-------!!!")
        for response_line in response.iter_lines():
            if response_line:
                json_response = json.loads(response_line)
                self.do_message(json_response)

    def do_message(self, json_message):
        body = markdown_strings.esc_format(json_message["data"]["text"])
        tickers = re.findall(self.ticker_pattern, body)
        if len(tickers) == 0:
            return
        tickers_string = " ".join(tickers).upper()
        author = json_message["matching_rules"][0]["tag"]

        self.telegram_bot.send_message(
            chat_id=secrets.CHAT_ID,
            text=f"*@{author} on {tickers_string}*\n\n{body}",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        print(
            """------@%s------\ntickers: %s\n%s\n\n"""
            % (author, " ".join(tickers), body)
        )

    def start_loop(self):
        bearer_token = secrets.BEARER_TOKEN
        headers = create_headers(bearer_token)
        rules = self.get_rules(headers, bearer_token)
        delete = self.delete_all_rules(headers, bearer_token, rules)
        set = self.set_rules(headers, bearer_token)
        while True:
            print("reconnecting")
            self.get_stream(headers, set, bearer_token)
            time.sleep(10)


def main():
    updater = Updater(telegram.Bot(token=secrets.BOT_TOKEN))
    updater.start_loop()


if __name__ == "__main__":
    main()
