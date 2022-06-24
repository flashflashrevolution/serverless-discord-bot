import json
import os
from typing import MutableMapping
from discord_interactions import (
    verify_key,
    InteractionType,
    InteractionResponseType,
    InteractionResponseFlags,
)


class UserObject:
    def __init__(self, username, type, me):
        self.username = username
        self.type = type
        self.me = me


def fail():
    return {
        "statusCode": 401,
    }


def get_user_object_with_id(member_object):
    return UserObject(
        username=member_object.get("user").get("id"), type="discord", me=True
    )


def get_user_object_with_username(user_obj):
    # May need to slice the username to remove the @ symbol.
    print(f"User Object: {user_obj}")
    return UserObject(username=user_obj.get("username"), type="discord", me=False)


def api_get(action, user: UserObject):
    from urllib import error, request

    try:
        FFR_API_URL = os.getenv("FFR_API_URL")
        FFR_API_KEY = os.getenv("FFR_API_KEY")
        req_string = f"{FFR_API_URL}?key={FFR_API_KEY}&action={action}&{user.type}={user.username}"
        print(f"Request string: {req_string}")
        return json.loads(request.urlopen(req_string).read(), timeout=1)
    except:
        return None


def main(args):
    PUBLIC_KEY = os.getenv("DISCORD_PUB_KEY")

    print(f"Arguments: {args}")  # debug print

    body = args.get("__ow_body")
    headers = args.get("__ow_headers")
    if body is None or headers is None:
        return fail()

    signature = headers.get("x-signature-ed25519")
    timestamp = headers.get("x-signature-timestamp")
    if (
        signature is None
        or timestamp is None
        or not verify_key(body.encode(), signature, timestamp, PUBLIC_KEY)
    ):
        return fail()

    body_json = json.loads(body)
    if body_json.get("type") == InteractionType.PING:
        return {
            "body": {"type": InteractionResponseType.PONG},
            "statusCode": 200,
        }
    elif body_json.get("type") == InteractionType.APPLICATION_COMMAND:
        command = body_json.get("data").get("name")
        print(f"Command: {command}")
        if command == "link":
            return {
                "body": {
                    "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                    "data": {
                        "content": "Please visit the following URL to link your discord account to FFR: https://www.flashflashrevolution.com/profiles/discord.php",
                        "flags": InteractionResponseFlags.EPHEMERAL,
                    },
                },
                "statusCode": 200,
            }
        elif command == "veteran":
            member_info = body_json.get("member")
            user_info = get_user_object_with_id(member_info)
            res = api_get("profile", user_info)

            # Invalid API response.
            if res is None or len(res) <= 0 or res.get("error_id") is not None:
                return {
                    "body": {
                        "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                        "data": {
                            "content": "No linked FFR account found. Use `/link` for instructions.",
                            "flags": InteractionResponseFlags.EPHEMERAL,
                        },
                    },
                    "statusCode": 200,
                }

            has_veteran_role = next(
                (
                    role
                    for role in member_info.get("roles")
                    if role == os.getenv("VETERAN_ROLE_ID")
                ),
                False,
            )
            print(res.get("roles"))
            print(member_info.get("roles"))
            print(f"Has Veteran Role: {has_veteran_role}")
            veteran_user_group = next(
                (x for x in res.get("roles") if x.get("id") == 49),
                None,
            )
            if has_veteran_role:
                return {
                    "body": {
                        "type": InteractionResponseType.DEFERRED_UPDATE_MESSAGE,
                        "data": {
                            "content": "You already have the Veteran role.",
                            "flags": InteractionResponseFlags.EPHEMERAL,
                        },
                    },
                    "statusCode": 200,
                }
            elif veteran_user_group is not None:
                return {
                    "body": {
                        "type": InteractionResponseType.DEFERRED_UPDATE_MESSAGE,
                        "data": {
                            "content": "Granting Veteran role.",
                            "flags": InteractionResponseFlags.EPHEMERAL,
                        },
                    },
                    "statusCode": 200,
                }

            return {
                "body": {
                    "type": InteractionResponseType.DEFERRED_UPDATE_MESSAGE,
                    "data": {
                        "content": "This command is not implemented.",
                        "flags": InteractionResponseFlags.EPHEMERAL,
                    },
                },
                "statusCode": 200,
            }

    print("Unknown interaction type.")
    return {"statusCode": 404}  # If no handler implemented for Discord's request
