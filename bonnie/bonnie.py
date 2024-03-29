import os
import random
import sys
import time
from dataclasses import dataclass
from typing import List

import orjson
import requests
from orso.tools import random_string

sys.path.insert(1, os.path.join(sys.path[0], "../hakatomi.com"))


@dataclass
class User:
    username: str
    password: str

    def make_auth_payload(self):
        if self.password is None:
            passwrd = "AAAA"
        else:
            passwrd = self.password

        return orjson.dumps({"username": self.username, "password": passwrd})


users = List[User]

HAKATOMI_URL: str = "http://localhost:8080/v1/authenticate"
RESET_URL: str = "http://localhost:8080/v1/user/reset"
DWELL: int = 0.25


def load_users():
    list_of_users = []
    with open("assets/users.txt", "r") as uf:
        for line in uf.readlines():
            username, password = line.split("\t")
            user = User(username, password[:-1])
            list_of_users.append(user)
    return list_of_users


def randomly_select_user() -> User:
    return random.choice(users)


def issue_request(user: User):
    try:
        attempt = requests.post(url=HAKATOMI_URL, data=user.make_auth_payload(), headers={"user-agent": user.username[0:5]})
    except Exception as e:
        print(e)
        return 900, ""

    print(user.username.ljust(20), attempt.text)

    return attempt.status_code, attempt.text


if __name__ == "__main__":

    users = load_users()

    while True:
        time.sleep(random.random() * 5)
        user = random.choice(users)
        username = user.username
        password = user.password
        if random.random() < 0.1:
            # 10% of the time get the username wrong
            username = random_string(8)
        if random.random() < 0.15:
            # 15% of the time, get the password wrong
            password = random_string(8)

        user_to_attempt = User(username, password)

        code, text = issue_request(user_to_attempt)

        if text == '"locked"' and random.random() < 0.01:
            print("resetting user", user.username)
            try:
                attempt = requests.post(url=RESET_URL, data=user.make_auth_payload(), headers={"user-agent": "bonnie"})
            except:
                pass

