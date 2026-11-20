# Fuel Route Planner — Run Guide and Demo Video

USA driving route with cost-optimal fuel stops. Vehicle range is 500 miles at 10 mpg. Fuel prices come from the included OPIS CSV. Routing uses one public OSRM call.

Python **3.12 or 3.13** is required (Django 6.1). An internet connection is required for routing and map tiles.

## 1. Setup

From the project root:

```bash
python --version
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Install and start:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py load_stations
python manage.py runserver 127.0.0.1:8000
```

`load_stations` takes about 30 seconds. A successful load looks like:

```text
Loaded 6614 stations (8124 unique US rows, 21 unmatched cities skipped).
```

Do not skip `load_stations`. Without it the map has no stations.

## 2. Open the app

- Map UI: http://127.0.0.1:8000/
- Example API: http://127.0.0.1:8000/api/route?start=Chicago,%20IL&finish=Dallas,%20TX

Use the **state and city dropdowns** only. Those lists are the cities that exist in the fuel-price CSV. Do not type random US towns.

The first route of a session usually takes 2–4 seconds (OSRM). Repeating the same pair is faster because the route is cached.

## 3. Demo video — record in this order

Keep the browser zoomed so the left sidebar and the map are both visible. After each Plan Route, pause long enough to read the numbers.

### Route 1 — Austin, TX → Dallas, TX (short)

1. Start: Texas / Austin. Finish: Texas / Dallas.
2. Click **Plan Route**.
3. Show the sidebar: Distance, Fuel cost, Gallons, and the fill-stop list.
4. Zoom the map. Orange markers are recommended fill-ups. Gray markers are other nearby stations along the route.
5. This route is about 198 miles and needs one fill.

### Route 2 — Chicago, IL → Dallas, TX (medium)

1. Start: Illinois / Chicago. Finish: Texas / Dallas.
2. Click **Plan Route**.
3. Show Distance, Fuel cost, Gallons, and every stop in the list (city, mile marker, $/gal, gallons, cost).
4. Pan the map along the route so several orange fills are visible.

### Route 3 — Buffalo, NY → Calexico, CA (long)

1. Start: New York / Buffalo. Finish: California / Calexico.
2. Click **Plan Route**. This one is slower because the drive is long.
3. Show the full sidebar: total distance, total gallons, **total fuel cost**, and the stop list from New York through Arizona/California.
4. Zoom out so fills are spread across the country, then zoom in on one or two orange stops. Gaps between fills stay under 500 miles.

### API response

Open a new tab:

http://127.0.0.1:8000/api/route?start=Chicago,%20IL&finish=Dallas,%20TX

Scroll the JSON so these fields are on camera:

- `distance_miles`
- `gallons_needed`
- `total_fuel_cost`
- `fuel_stops` (city, state, price, gallons, cost, mile)

That is the same plan the map uses.

## 4. What the numbers mean

- Tank starts **empty**.
- Fuel needed for the trip is `distance_miles / 10`.
- Prices are the cheapest CSV price per OPIS station ID.
- The optimizer picks fill-ups so the truck can finish the trip without running dry, preferring cheaper stations ahead when they are still in range.

## 5. If something fails

| What you see | What to do |
| --- | --- |
| `python --version` is 3.11 or lower | Install Python 3.12+ and recreate `.venv` |
| Install fails on Django 6.1 | Same: wrong Python version |
| `No fuel stations` / empty dropdowns | Run `python manage.py load_stations` from the project root. Confirm `data/fuel-prices-for-be-assessment.csv` and `data/us_places.csv` are present |
| Map tiles look broken / 403 | Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (macOS) |
| Route request times out | Public OSRM can flake. Wait ~30 seconds and try the same pair again. Internet must be on |

Optional checks after setup:

```bash
python -m pytest
```
