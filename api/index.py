import requests
import random
from flask import Flask, jsonify, request

class GameInfo:
    def __init__(self):
        self.TitleId : str = "1478E5"
        self.SecretKey : str = "WPMTQBKWP4ZHIXEKXC9B55M4UTZ33PW86T44EXJSOWYWWO3H4A"
        self.ApiKey : str = "OC|6743687609024930|e9fbf64dd4e4b62f486d8532f7584732"

    def get_auth_headers(self):
        return {
            "content-type": "application/json",
            "X-SecretKey": self.SecretKey
        }

settings = GameInfo()
app = Flask(__name__)
playfab_cache = {}
mute_cache = {}

def return_function_json(data, funcname, funcparam={}):
    user_id = data["FunctionParameter"]["CallerEntityProfile"]["Lineage"]["TitlePlayerAccountId"]

    response = requests.post(
        url=f"https://{settings.TitleId}.playfabapi.com/Server/ExecuteCloudScript",
        json={
            "PlayFabId": user_id,
            "FunctionName": funcname,
            "FunctionParameter": funcparam
        },
        headers=settings.get_auth_headers()
    )

    if response.status_code == 200:
        return jsonify(response.json().get("data").get("FunctionResult")), response.status_code
    else:
        return jsonify({}), response.status_code

def get_is_nonce_valid(nonce, oculus_id):
    response = requests.post(
        url=f'https://graph.oculus.com/user_nonce_validate?nonce={nonce}&user_id={oculus_id}&access_token={settings.ApiKey}',
        url1=f'https://graph.oculus.com/user_nonce_validate?nonce={nonce}&user_id={oculus_id}&access_token={settings.ApiKey1}',
        headers={"content-type": "application/json"}
    )
    return response.json().get("is_valid")

@app.route("/", methods=["POST", "GET"])
def main():
    return "Service is running"

@app.route("/api/PlayFabAuthentication", methods=["POST"])
def playfab_authentication():
    rjson = request.get_json()
    required_fields = ["CustomId", "Nonce", "AppId", "Platform", "OculusId"]
    missing_fields = [field for field in required_fields if not rjson.get(field)]

    if missing_fields:
        return jsonify({
            "Message": f"Missing parameter(s): {', '.join(missing_fields)}",
            "Error": f"BadRequest-No{missing_fields[0]}"
        }), 400

    if rjson.get("AppId") != settings.TitleId:
        return jsonify({
            "Message": "Request sent for the wrong App ID",
            "Error": "BadRequest-AppIdMismatch"
        }), 400

    if not rjson.get("CustomId").startswith(("OC", "PI")):
        return jsonify({
            "Message": "Bad request",
            "Error": "BadRequest-NoOCorPIPrefix"
        }), 400

    url = f"https://{settings.TitleId}.playfabapi.com/Server/LoginWithServerCustomId"
    login_request = requests.post(
        url=url,
        json={
            "ServerCustomId": rjson.get("CustomId"),
            "CreateAccount": True
        },
        headers=settings.get_auth_headers()
    )

    if login_request.status_code == 200:
        data = login_request.json().get("data")
        session_ticket = data.get("SessionTicket")
        entity_token = data.get("EntityToken").get("EntityToken")
        playfab_id = data.get("PlayFabId")
        entity_type = data.get("EntityToken").get("Entity").get("Type")
        entity_id = data.get("EntityToken").get("Entity").get("Id")

        link_response = requests.post(
            url=f"https://{settings.TitleId}.playfabapi.com/Server/LinkServerCustomId",
            json={
                "ForceLink": True,
                "PlayFabId": playfab_id,
                "ServerCustomId": rjson.get("CustomId"),
            },
            headers=settings.get_auth_headers()
        ).json()

        return jsonify({
            "PlayFabId": playfab_id,
            "SessionTicket": session_ticket,
            "EntityToken": entity_token,
            "EntityId": entity_id,
            "EntityType": entity_type
        }), 200
    else:
        error_details = login_request.json().get('errorDetails')
        first_error = next(iter(error_details))
        return jsonify({
            "ErrorMessage": str(first_error),
            "ErrorDetails": error_details[first_error]
        }), login_request.status_code

@app.route("/api/CachePlayFabId", methods=["POST"])
def cache_playfab_id():
    rjson = request.get_json()
    playfab_cache[rjson.get("PlayFabId")] = rjson
    return jsonify({"Message": "Success"}), 200

@app.route("/api/tdd", methods=["POST", "GET"])
def title_data():
    response = requests.post(
        url=f"https://{settings.TitleId}.playfabapi.com/Server/GetTitleData",
        headers=settings.get_auth_headers()
    )

    if response.status_code == 200:
        return jsonify(response.json().get("data").get("Data"))
    else:
        return jsonify({}), response.status_code

@app.route('/api/dtd', methods=['POST', 'GET'])
def titled_data():
    return jsonify({"MOTD":"<color=yellow>WELCOME TO RAINBOW TAG!</color>\n\n<color=red>SCIENCE UPDATE! WE CAN DO NEWER UPDATES!</color>\n\n\n<color=magenta>DISCORD.GG/RAINBOWTAG!</color>\n<color=orange>CREDITS: QWIZX, NM13L</color>"})

@app.route("/api/CheckForBadName", methods=["POST"])
def check_for_bad_name():
    rjson = request.get_json().get("FunctionResult")
    name = rjson.get("name").upper()

    if name in ["KKK", "PENIS", "NIGG", "NEG", "NIGA", "MONKEYSLAVE", "SLAVE", "FAG", 
        "NAGGI", "TRANNY", "QUEER", "KYS", "DICK", "PUSSY", "VAGINA", "BIGBLACKCOCK", 
        "DILDO", "HITLER", "KKX", "XKK", "NIGA", "NIGE", "NIG", "NI6", "PORN", 
        "JEW", "JAXX", "TTTPIG", "SEX", "COCK", "CUM", "FUCK", "PENIS", "DICK", 
        "ELLIOT", "JMAN", "K9", "NIGGA", "TTTPIG", "NICKER", "NICKA", 
        "REEL", "NII", "@here", "!", " ", "JMAN", "PPPTIG", "CLEANINGBOT", "JANITOR", "K9", 
        "H4PKY", "MOSA", "NIGGER", "NIGGA", "IHATENIGGERS", "@everyone", "TTT"]:
        return jsonify({"result": 2})
    else:
        return jsonify({"result": 0})

@app.route("/api/GetAcceptedAgreements", methods=["POST", "GET"])
def get_accepted_agreements():
    rjson = request.get_json()["FunctionResult"]
    return jsonify(rjson)

@app.route("/api/SubmitAcceptedAgreements", methods=["POST", "GET"])
def submit_accepted_agreements():
    rjson = request.get_json()["FunctionResult"]
    return jsonify(rjson)

@app.route("/api/GetRandomName", methods=["POST", "GET"])
def get_random_name():
    return jsonify({"result": f"gorilla{random.randint(1000, 9999)}"})

@app.route("/api/ConsumeOculusIAP", methods=["POST"])
def consume_oculus_iap():
    rjson = request.get_json()

    access_token = rjson.get("userToken")
    user_id = rjson.get("userID")
    nonce = rjson.get("nonce")
    sku = rjson.get("sku")

    response = requests.post(
        url=f"https://graph.oculus.com/consume_entitlement?nonce={nonce}&user_id={user_id}&sku={sku}&access_token={settings.ApiKey}",
        headers={"content-type": "application/json"}
    )

    if response.json().get("success"):
        return jsonify({"result": True})
    else:
        return jsonify({"error": True})

@app.route("/api/ReturnMyOculusHashV2")
def return_my_oculus_hash_v2():
    return return_function_json(request.get_json(), "ReturnMyOculusHash")

@app.route("/api/ReturnCurrentVersionV2", methods=["POST", "GET"])
def return_current_version_v2():
    return return_function_json(request.get_json(), "ReturnCurrentVersion")

@app.route("/api/TryDistributeCurrencyV2", methods=["POST", "GET"])
def try_distribute_currency_v2():
    return return_function_json(request.get_json(), "TryDistributeCurrency")

@app.route("/api/BroadCastMyRoomV2", methods=["POST", "GET"])
def broadcast_my_room_v2():
    return return_function_json(request.get_json(), "BroadCastMyRoom", request.get_json()["FunctionParameter"])

@app.route("/api/ShouldUserAutomutePlayer", methods=["POST", "GET"])
def should_user_automute_player():
    return jsonify(mute_cache)

@app.route("/api/photon/authenticate", methods=["POST"])
def photon_authenticate():
    user_id = request.args.get("username")
    token = request.args.get("token")

    if user_id is None or len(user_id) != 16:
        return jsonify({'resultCode': 2, 'message': 'Invalid token', 'userId': None, 'nickname': None})

    if token is None:
        return jsonify({'resultCode': 3, 'message': 'Failed to parse token from request', 'userId': None, 'nickname': None})

    try:
        response = requests.post(
            url=f"https://{settings.TitleId}.playfabapi.com/Server/GetUserAccountInfo",
            json={"PlayFabId": user_id},
            headers=settings.get_auth_headers()
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({'resultCode': 0, 'message': f"Something went wrong: {str(e)}", 'userId': None, 'nickname': None})

    try:
        user_info = response.json().get("UserInfo", {}).get("UserAccountInfo", {})
        nickname = user_info.get("Username", None)
    except (ValueError, KeyError, TypeError) as e:
        return jsonify({'resultCode': 0, 'message': f"Error parsing response: {str(e)}", 'userId': None, 'nickname': None})

    return jsonify({
        'resultCode': 1,
        'message': f'Authenticated user {user_id.lower()} title {settings.TitleId.lower()}',
        'userId': user_id.upper(),
        'nickname': nickname
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
