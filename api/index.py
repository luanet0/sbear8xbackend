import requests
import random
from flask import Flask, jsonify, request, abort
from functools import wraps

# ------------------------- CONFIG -------------------------
class GameInfo:
    def __init__(self):
        self.TitleId: str = "1478E5"
        self.SecretKey: str = "WPMTQBKWP4ZHIXEKXC9B55M4UTZ33PW86T44EXJSOWYWWO3H4A"
        self.ApiKey: str = "OC|6743687609024930|e9fbf64dd4e4b62f486d8532f7584732"

    def auth_headers(self):
        return {
            "Content-Type": "application/json",
            "X-SecretKey": self.SecretKey
        }


settings = GameInfo()
app = Flask(__name__)

# ------------------------- CACHES -------------------------
playfab_cache = {}
mute_cache = {}

# ------------------------- UTILITIES -------------------------
def validate_json(fields):
    """Decorator to validate required JSON fields"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({"Error": "Missing JSON payload"}), 400
            missing = [field for field in fields if not data.get(field)]
            if missing:
                return jsonify({"Message": f"Missing parameter(s): {', '.join(missing)}",
                                "Error": f"BadRequest-No{missing[0]}"}), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator


def execute_cloud_function(data, func_name, func_params={}):
    """Execute a PlayFab cloud function"""
    try:
        user_id = data["FunctionParameter"]["CallerEntityProfile"]["Lineage"]["TitlePlayerAccountId"]
        resp = requests.post(
            url=f"https://{settings.TitleId}.playfabapi.com/Server/ExecuteCloudScript",
            json={
                "PlayFabId": user_id,
                "FunctionName": func_name,
                "FunctionParameter": func_params
            },
            headers=settings.auth_headers(),
            timeout=10
        )
        resp.raise_for_status()
        return jsonify(resp.json().get("data", {}).get("FunctionResult", {})), 200
    except requests.RequestException:
        return jsonify({}), 500


def check_bad_name(name: str):
    """Check if the name contains forbidden words"""
    forbidden = {
        "KKK", "PENIS", "NIGG", "NEG", "NIGA", "MONKEYSLAVE", "SLAVE",
        "FAG", "NAGGI", "TRANNY", "QUEER", "KYS", "DICK", "PUSSY", "VAGINA",
        "BIGBLACKCOCK", "DILDO", "HITLER", "KKX", "XKK", "NIGE", "NI6", "PORN",
        "JEW", "JAXX", "TTTPIG", "SEX", "COCK", "CUM", "FUCK", "@here", "@everyone"
    }
    return name.upper() in forbidden


# ------------------------- ROUTES -------------------------
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "Service is running"})


@app.route("/api/PlayFabAuthentication", methods=["POST"])
@validate_json(["CustomId", "Nonce", "AppId", "Platform", "OculusId"])
def playfab_authentication():
    rjson = request.get_json()

    # Validate AppId
    if rjson.get("AppId") != settings.TitleId:
        return jsonify({"Message": "Wrong App ID", "Error": "BadRequest-AppIdMismatch"}), 400

    # Validate CustomId prefix
    if not rjson.get("CustomId").startswith(("OC", "PI")):
        return jsonify({"Message": "Bad request", "Error": "BadRequest-NoOCorPIPrefix"}), 400

    try:
        # Login or create PlayFab account
        login_resp = requests.post(
            url=f"https://{settings.TitleId}.playfabapi.com/Server/LoginWithServerCustomId",
            json={"ServerCustomId": rjson.get("CustomId"), "CreateAccount": True},
            headers=settings.auth_headers(),
            timeout=10
        )
        login_resp.raise_for_status()
        data = login_resp.json()["data"]

        # Link server custom ID
        requests.post(
            url=f"https://{settings.TitleId}.playfabapi.com/Server/LinkServerCustomId",
            json={"ForceLink": True, "PlayFabId": data["PlayFabId"], "ServerCustomId": rjson.get("CustomId")},
            headers=settings.auth_headers(),
            timeout=10
        )

        entity = data["EntityToken"]["Entity"]
        return jsonify({
            "PlayFabId": data["PlayFabId"],
            "SessionTicket": data["SessionTicket"],
            "EntityToken": data["EntityToken"]["EntityToken"],
            "EntityId": entity["Id"],
            "EntityType": entity["Type"]
        }), 200

    except requests.RequestException as e:
        return jsonify({"Error": str(e)}), 500


@app.route("/api/CachePlayFabId", methods=["POST"])
@validate_json(["PlayFabId"])
def cache_playfab_id():
    rjson = request.get_json()
    playfab_cache[rjson.get("PlayFabId")] = rjson
    return jsonify({"Message": "Cached successfully"}), 200


@app.route("/api/tdd", methods=["GET"])
def get_title_data():
    try:
        resp = requests.post(
            url=f"https://{settings.TitleId}.playfabapi.com/Server/GetTitleData",
            headers=settings.auth_headers(),
            timeout=10
        )
        resp.raise_for_status()
        return jsonify(resp.json().get("data", {}).get("Data", {})), 200
    except requests.RequestException:
        return jsonify({}), 500


@app.route("/api/dtd", methods=["GET"])
def get_titled_data():
    return jsonify({
        "MOTD": "<color=yellow>WELCOME TO RAINBOW TAG!</color>\n\n"
                "<color=red>SCIENCE UPDATE! WE CAN DO NEWER UPDATES!</color>\n\n"
                "<color=magenta>DISCORD.GG/RAINBOWTAG!</color>\n"
                "<color=orange>CREDITS: QWIZX, NM13L</color>"
    })


@app.route("/api/CheckForBadName", methods=["POST"])
@validate_json(["FunctionResult"])
def api_check_bad_name():
    rjson = request.get_json()["FunctionResult"]
    name = rjson.get("name", "")
    return jsonify({"result": 2 if check_bad_name(name) else 0})


@app.route("/api/GetRandomName", methods=["GET"])
def get_random_name():
    return jsonify({"result": f"gorilla{random.randint(1000, 9999)}"})


@app.route("/api/ReturnMyOculusHashV2", methods=["POST"])
def return_oculus_hash_v2():
    return execute_cloud_function(request.get_json(), "ReturnMyOculusHash")


@app.route("/api/ReturnCurrentVersionV2", methods=["GET"])
def return_current_version_v2():
    return execute_cloud_function(request.get_json(), "ReturnCurrentVersion")


@app.route("/api/TryDistributeCurrencyV2", methods=["GET"])
def try_distribute_currency_v2():
    return execute_cloud_function(request.get_json(), "TryDistributeCurrency")


@app.route("/api/BroadCastMyRoomV2", methods=["GET"])
def broadcast_my_room_v2():
    data = request.get_json().get("FunctionParameter", {})
    return execute_cloud_function(request.get_json(), "BroadCastMyRoom", data)


@app.route("/api/ShouldUserAutomutePlayer", methods=["GET"])
def should_user_automute_player():
    return jsonify(mute_cache)


# ------------------------- MAIN -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
