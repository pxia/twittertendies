#!/usr/bin/env python3

import time
import requests
import os
import ujson as json
import re
import telegram
import secrets
import html

FOLLOWS = [
    "alexcutler247",
    "anandchokkavelu",
    "Beth_Kindig",
    "ChrisRandone",
    "CitronResearch",
    "DeItaone",
    "garyblack00",
    "Mitch___Picks",
    "MrZackMorris",
    "OphirGottlieb",
    "PJ_Matlock",
    "RadioSilentplay",
    "StockLizardKing",
    "The_RockTrading",
    "TheStockGuyTV",
    "Ultra_Calls",
    "yatesinvesting",
]


def create_headers(bearer_token):
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers


class Updater:
    def __init__(self, telegram_bot):
        self.telegram_bot = telegram_bot
        self.ticker_pattern = re.compile("\$[A-Za-z]{1,6}")

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
        body = html.unescape(json_message["data"]["text"])
        tweet_id = json_message["data"]["id"]
        tickers = set(map(lambda s: s.upper(), re.findall(self.ticker_pattern, body)))
        if len(tickers) == 0:
            return

        # link to yahoo finance
        tickers_string = " ".join(
            map(
                lambda s: "[%s](https://finance.yahoo.com/quote/%s)"
                % (s.upper(), s[1:].lower()),
                tickers,
            )
        )
        author = telegram.utils.helpers.escape_markdown(
            text=json_message["matching_rules"][0]["tag"], version=2
        )

        # probably fine do this then html escape and markdown escape?
        # link to twitter search
        processed_body = re.sub(
            self.ticker_pattern,
            lambda m: "[%s](https://twitter.com/search?q=%s&src=cashtag_click)"
            % (m.group(0), html.escape(m.group(0))),
            telegram.utils.helpers.escape_markdown(text=body, version=2),
        )

        text = f"*[@{author}](https://twitter.com/{author}/status/{tweet_id}) on {tickers_string}*\n\n{processed_body}"
        self.telegram_bot.send_message(
            chat_id=secrets.CHAT_ID,
            text=text,
            parse_mode="MarkdownV2",
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
            try:
                self.get_stream(headers, set, bearer_token)
            except Exception as err:
                print(err)
            time.sleep(10)


def main():
    updater = Updater(telegram.Bot(token=secrets.BOT_TOKEN))
    updater.start_loop()


if __name__ == "__main__":
    main()
