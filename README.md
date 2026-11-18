# MOBILUX — Academic Presentation Prototype

A deliberately simple Flask + SQLite website for a Tourism & Hospitality academic presentation.

## Run
1. Install Python 3.10+.
2. In this folder, run `python -m venv .venv`
3. Activate it:
   - Windows: `.venv\\Scripts\\activate`
   - macOS/Linux: `source .venv/bin/activate`
4. Run `pip install -r requirements.txt`
5. Run `python app.py`
6. Open http://127.0.0.1:5000

The SQLite database is created automatically as `mobilux.db`.

## Included
- Homepage and brand presentation
- MOBILUX CITY and MOBILUX NATURE package pages
- Predefined example itineraries
- Booking request form
- Optional experience selection
- Demo confirmation reference
- My Journey lookup by reference and email

## Intentionally not included
No real users/accounts, authentication, payment, external APIs, real vehicle availability, geolocation tracking, routing, dispatch or live pick-up inventory. Booking requests are academic demonstration records only. Pick-up is entered manually. The map and travel operations can be explained as proposed future functionality in the presentation.
