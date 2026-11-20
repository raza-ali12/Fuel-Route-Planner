RANGE_MILES = 500.0
MPG = 10.0
TANK_GALLONS = RANGE_MILES / MPG
CORRIDOR_MILES = 30.0
ORIGIN_WINDOW_MILES = 50.0
CHEAP_FILL_LOOKAHEAD_MILES = 250.0
MIN_HOP_MILES = 30.0
ROUTE_SAMPLE_MILES = 2.0
GRID_CELL_DEGREES = 0.2
OSRM_CACHE_DECIMALS = 4
HIGHWAY_MATCH_MILES = 80.0

US_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

US_STATE_CODES = set(US_STATE_NAMES)

ASSUMPTIONS = {
    "start_tank": "empty",
    "station_locations": "snapped to route from city/highway match",
    "corridor_miles": CORRIDOR_MILES,
}
