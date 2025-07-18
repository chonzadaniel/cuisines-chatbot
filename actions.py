# ----------------------- IMPORT LIBRARIES ---------------------------------------
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import requests
from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

logger = logging.getLogger(__name__)

# ZOMATO CONFIG
ZOMATO_API_KEY = 'your_api_key'
ZOMATO_API_URL = 'https://developers.zomato.com/api/v2.1/'
ZOMATO_HEADERS = {
    'User-agent': 'rasa-bot/1.0',
    'Accept': 'application/json',
    'user_key': ZOMATO_API_KEY
}

# GOOGLE PLACES CONFIG
GOOGLE_PLACES_API_KEY = 'your_api_key'
GOOGLE_PLACES_API_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'

class ActionRestaurantSearch(Action):
    def name(self) -> Text:
        return "action_restaurant_search"

    def parse_zomato(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        restaurants = []
        for item in response.get('restaurants', []):
            r = item['restaurant']
            restaurants.append({
                'name': r['name'],
                'cuisines': r['cuisines'],
                'address': r['location']['address'],
                'rating': r['user_rating']['aggregate_rating'],
                'cost': r['average_cost_for_two']
            })
        return restaurants

    def get_zomato_location(self, location: Text) -> Optional[Dict[str, str]]:
        url = f"{ZOMATO_API_URL}locations?query={location}"
        res = requests.get(url, headers=ZOMATO_HEADERS)

        if res.ok and res.json().get('location_suggestions'):
            loc = res.json()['location_suggestions'][0]
            return {'lat': str(loc['latitude']), 'lon': str(loc['longitude'])}

        return None

    def fallback_google_places(self, cuisine: Text, location: Text) -> List[Dict[str, Any]]:
        logger.info("Trying Google Places fallback")
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={GOOGLE_PLACES_API_KEY}"
        geo_res = requests.get(geocode_url).json()

        if not geo_res['results']:
            return []

        latlng = geo_res['results'][0]['geometry']['location']
        lat, lon = latlng['lat'], latlng['lng']

        params = {
            'location': f"{lat},{lon}",
            'radius': 5000,
            'type': 'restaurant',
            'keyword': cuisine,
            'key': GOOGLE_PLACES_API_KEY
        }

        res = requests.get(GOOGLE_PLACES_API_URL, params=params).json()

        results = []
        for r in res.get('results', []):
            results.append({
                'name': r.get('name'),
                'cuisines': cuisine,
                'address': r.get('vicinity'),
                'rating': r.get('rating', 'N/A'),
                'cost': 'N/A'
            })
        return results

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        location = tracker.get_slot('location')
        cuisine = tracker.get_slot('cuisine')

        if not location:
            dispatcher.utter_message(response="utter_ask_location")
            return []
        if not cuisine:
            dispatcher.utter_message(response="utter_ask_cuisine")
            return []

        dispatcher.utter_message(f"Looking for {cuisine} restaurants in {location}…")

        zomato_coords = self.get_zomato_location(location)
        restaurants = []

        if zomato_coords:
            zomato_url = (
                f"{ZOMATO_API_URL}search?q={cuisine}&lat={zomato_coords['lat']}&lon={zomato_coords['lon']}&sort=rating"
            )
            zomato_res = requests.get(zomato_url, headers=ZOMATO_HEADERS)

            if zomato_res.ok:
                restaurants = self.parse_zomato(zomato_res.json())

        if not restaurants:
            dispatcher.utter_message("Couldn’t find any results on Zomato. Let me check another source…")
            restaurants = self.fallback_google_places(cuisine, location)

        if restaurants:
            dispatcher.utter_message(f"Here are some {cuisine} places in {location}:")
            for r in restaurants[:5]:
                dispatcher.utter_message(
                    f"*{r['name']}*\n"
                    f"Cuisines: {r['cuisines']}\n"
                    f"Address: {r['address']}\n"
                    f"Rating: {r['rating']}\n"
                    f"Cost for two: {r['cost']}"
                )
        else:
            dispatcher.utter_message("Sorry, I couldn’t find any restaurants. Please try another cuisine or location!")

        return []
