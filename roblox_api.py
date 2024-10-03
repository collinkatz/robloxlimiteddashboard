import requests
import pandas as pd
import time
import streamlit as st
import json

class custom_session:

    def output_errors(self, response, url, data=None, json=None, x_csrf_request=False, type="GET"):
        """ Output the errors of a response if there are any along with some information about it
        Note: if x_csrf_request is true the error will not be output since most of the time x-csrf-token requests error
        the x-csrf-token is needed to make api calls but when this service already has a valid one the server returns an error
        :param response: The response object returned by some request (get, post, etc.)
        :param url: The url of the request
        :param x_csrf_request: True or False, whether or not this is an x-csrf-token request
        :param type: The type of request GET or POST
        """

        # Check if error response and is not an x-csrf-token request
        if (response.status_code >= 300 or "errors" in response.json().keys()) and x_csrf_request == False:
            print("Error ", type, response.status_code, ":")
            print("Request URL:", url)
            print("Request Json:", json)
            print("Response Headers:", response.headers)
            print("Response JSON:", response.json())
            print("\n")


    def __init__(self, session: requests.Session):
        """ Create a new custom session
        :param session: The session that this custom session class wraps
        """
        self.session = session
        self.headers = {}
        self.last_x_csrf_request_time = -1 # Default value ig since app doesn't start with one so make it greater than 20 mins

    def set_header(self, header_name, header_data):
        """ Sets session headers for the session
        :param header_name: The name of the header to set
        :param header_data: The data to set in the header
        """
        print("header_name:", header_name, "header_data:", header_data)
        self.headers[header_name] = header_data
        self.session.headers[header_name] = header_data

    def get(self, url, x_csrf_request=False, **kwargs):
        """GET request, same syntax as requests.get"""
        print("GET:", url)
        # time.sleep(0.25)
        response = self.session.get(url, **kwargs)
        self.output_errors(response, url, x_csrf_request=x_csrf_request, type="GET")
        while response.status_code == 429:
            # time.sleep(int(response.headers["retry-after"])) # retry-after header should be included in response headers, but its not thanks roblox
            time.sleep(10)
            print("429 response, retrying...")
            refresh_session_headers(self, force=True)
            response = self.session.get(url, **kwargs) # Recursive step
        return response

    def post(self, url, data=None, json=None, x_csrf_request=False, **kwargs):
        """POST request, same syntax as requests.post"""
        print("POST:", url, json)
        time.sleep(2)
        response = self.session.post(url, data=data, json=json, **kwargs)
        self.output_errors(response, url, data=data, json=json, x_csrf_request=x_csrf_request, type="POST")
        while response.status_code == 429:
            # time.sleep(int(response.headers["retry-after"])) # retry-after header should be included in response headers, but its not thanks roblox
            time.sleep(10)
            print("429 response, retrying...")
            refresh_session_headers(self, force=True)
            response = self.session.post(url, data=data, json=json, **kwargs) # Recursive step
        return response
    
    def need_new_x_csrf_token(self):
        """ Determines if this session needs a new x-csrf-token based on the age of the last token stored in this class.
        :note: A new x-csrf-token is needed around once every 5 minutes.
        """
        last = self.last_x_csrf_request_time
        now = time.perf_counter()
        x_csrf_token_age = now - last
        if self.last_x_csrf_request_time == -1: # If the session doesn't have one yet
            self.last_x_csrf_request_time = now
            return True
        elif x_csrf_token_age >= 300: # Should grab it every 5 mins
            self.last_x_csrf_request_time = now
            return True
        else:
            return False

@st.cache_data
def get_user_session():
    """Gets a custom_session to be used by the application and sets the ROBLOSECURITY cookie"""
    roblosecurity = open("roblosecurity.txt", "r").read()

    # Setup Session
    session = requests.Session()
    session.cookies[".ROBLOSECURITY"] = roblosecurity

    new_session = custom_session(session)

    return new_session

def get_x_csrf_token(_session: custom_session):
    """ Return a x-csrf-token to access api
    :param _session: The custom_session in use
    """
    req = _session.post(url="https://auth.roblox.com/v2/login", x_csrf_request=True)
    # print("x-csrf-token:", req.headers["x-csrf-token"])
    
    csrf_token = req.headers.get("x-csrf-token")
    if not csrf_token:
        raise ValueError("x-csrf-token not found in response headers")
    
    print("x-csrf-token found")
    return csrf_token

def refresh_session_headers(_session: custom_session, force=False):
    """ Refresh the session headers such as the x-csrf token.
    :param _session: The custom_session in use
    :param force: Forces the refresh regardless of whether or not a new x-csrf-token is needed
    """
    if _session.need_new_x_csrf_token() or force:
        print("...Refreshing session headers...")
        try:
            csrf_token = get_x_csrf_token(_session)

            # Set session headers
            _session.set_header("Referer", "https://www.roblox.com")
            _session.set_header("x-csrf-token", csrf_token)
            _session.set_header("content-type", "application/json")
        except Exception as e:
            print(f"Error refreshing session headers: {e}")

@st.cache_data
def get_asset_id(_session: custom_session, *item_ids):

    refresh_session_headers(_session)

    detail_content = get_item_detail_data(_session, *item_ids)

    ids = []
    types = []
    for item in detail_content:
        try:
            ids.append(item["collectibleItemId"])
            types.append("limitedUnique")
        except KeyError as e:
            ids.append(item["id"])
            types.append("limited")

    return ids, types

@st.cache_data
def get_item_detail_data(_session: custom_session, *item_ids):

    refresh_session_headers(_session)

    # Create payload to get data on items
    payload = {
        "items": [ { "itemType": 1, "id": item_id } for item_id in item_ids ]
    }
    print("\nFOUND", { "itemType": 1, "id": 14520285147 } in payload["items"], "FOUND\n")

    response = _session.post("https://catalog.roblox.com/v1/catalog/items/details", json=payload)
    return response.json()["data"]

@st.cache_data(ttl=1800) # Refresh cash after 30 minutes
def get_resale_data(_session: custom_session, *item_ids):

    refresh_session_headers(_session)

    asset_ids, item_types = get_asset_id(_session, *item_ids)

    id_to_price_volume = {} # Dict holding our price and volume data for each item id
    for i in range(len(asset_ids)):
        asset_id = asset_ids[i]
        item_type = item_types[i]

        # Make different requests based on item types
        response = None
        if item_type == "limited":
            response = _session.get("https://economy.roblox.com/v1/assets/" + str(asset_id) + "/resale-data").json()
        elif item_type == "limitedUnique":
            response = _session.get("https://apis.roblox.com/marketplace-sales/v1/item/" + str(asset_id) + "/resale-data").json()

        # Separate price and volume from response
        price = response["priceDataPoints"]
        volume = response["volumeDataPoints"]
        # Create Dataframe
        df_price = pd.DataFrame(price)
        df_volume = pd.DataFrame(volume)
        # Change date column to datetime objects for ease of use
        df_price["date"] = pd.to_datetime(df_price["date"])
        df_volume["date"] = pd.to_datetime(df_volume["date"])
        
        id_to_price_volume[asset_id] = {"price": df_price, "volume": df_volume}

    return id_to_price_volume

# TODO: Make sure you can also get UGC Items
# https://inventory.roblox.com/v2/users/{User Id}/inventory/{assetTypeId: 8, 19, 42, 43, 44, 45, 46, 47 <- All accessory types}?cursor=&limit=100&sortOrder=Desc
# Use above endpoint to get the items in inventory and iterate through to find things like this
# {
# "userAssetId": 205798681007,
# "assetId": 14011666016,
# "assetName": "Exclamation Gold",
# "collectibleItemId": "35805b62-bf15-4e2e-9e0c-14bd019567d1",
# "collectibleItemInstanceId": "f28a3e28-840c-4678-88cb-0e40c23f45bd",
# "serialNumber": 36,
# "owner": {
#     "userId": 19882314,
#     "username": "giantsnailbob",
#     "buildersClubMembershipType": 0
# },
# "created": "2023-07-10T03:24:40.543Z",
# "updated": "2023-07-10T03:24:40.543Z"
# },
# Where the collectibleItemId is not null
def get_user_limited_items(_session: custom_session, user_id):

    page_size = 10
    
    refresh_session_headers(_session)

    response = _session.get("https://inventory.roblox.com/v1/users/" + str(user_id) + "/assets/collectibles?limit=" + str(page_size) + "&sortOrder=Asc").json()
    df = pd.DataFrame(response["data"])

    while response["nextPageCursor"] is not None:
        next_page_cursor = response["nextPageCursor"]
        response = _session.get("https://inventory.roblox.com/v1/users/" + str(user_id) + "/assets/collectibles?cursor=" + next_page_cursor + "&limit=" + str(page_size) + "&sortOrder=Asc").json()
        new_df = pd.DataFrame(response["data"])
        df = pd.concat([df, new_df])

    return df

def get_item_link(asset_id):
    return "https://www.roblox.com/catalog/" + str(asset_id) + "/"

@st.cache_data
def get_item_preview_thumbnail(_session: custom_session, asset_id):

    refresh_session_headers(_session)

    response = _session.get("https://thumbnails.roblox.com/v1/assets?assetIds=" + str(asset_id) + "&returnPolicy=PlaceHolder&size=30x30&format=Png&isCircular=false")

    return response.json()["data"][0]["imageUrl"]