import streamlit as st
import pandas as pd
import roblox_api

# test item id 14520285147
# Shaggy is 20573078
# user id 19882314

print("\nRestarting StreamLit Application\n", "-----------------------------------------------", "\n")

session = roblox_api.get_user_session()
user_limiteds = roblox_api.get_user_limited_items(session, 19882314)
# resale_data = roblox_api.get_resale_data(session, 20573078)["price"]["value"].to_list()
# user_limiteds["timeseries"] = [resale_data for i in user_limiteds.index]

# Get important timeseries price data. Takes a while just let it run.
# user_limiteds["timeseries"] = user_limiteds.apply(lambda item: roblox_api.get_resale_data(session, item["assetId"])["price"]["value"].to_list(), axis=1)

# Drop unimportant data from DF or just grab the ones we want
# user_limiteds.drop(["userAssetId", "assetId", "assetStock", "serialNumber", "buildersClubMembershipType", "isOnHold"], axis=1)

updated_user_limiteds = pd.DataFrame()
updated_user_limiteds["preview"] = user_limiteds.apply(lambda item: roblox_api.get_item_preview_thumbnail(session, item["assetId"]), axis=1)
updated_user_limiteds["name"] = user_limiteds["name"]
updated_user_limiteds["link"] = user_limiteds.apply(lambda item: roblox_api.get_item_link(item["assetId"]), axis=1)
updated_user_limiteds["originalPrice"] = user_limiteds["originalPrice"]
updated_user_limiteds["recentAveragePrice"] = user_limiteds["recentAveragePrice"]

id_to_price_volume_dict = roblox_api.get_resale_data(session, *user_limiteds["assetId"].to_list())
updated_user_limiteds["timeseries"] = user_limiteds.apply(lambda item: id_to_price_volume_dict[item["assetId"]]["price"]["value"].to_list()[::-1], axis=1)

st.data_editor(
    updated_user_limiteds,
    column_config={
        "timeseries": st.column_config.LineChartColumn(
            "Sales (last 6 months)",
            width="medium",
            help="The sales volume in the last 6 months",
            y_min=0,
            y_max=100,
        ),
        "link": st.column_config.LinkColumn(
            "Link to item",
            display_text="here"
        ),
        "preview": st.column_config.ImageColumn(
            "Item Preview"
        )
    },
    hide_index=True,
)