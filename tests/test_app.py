import re
import tempfile
import unittest
from pathlib import Path

import app as mobilux
from i18n import CATALOGS, missing_keys


class MobiluxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        mobilux.DB = Path(self.tmp.name) / "test.db"
        mobilux.init_db()
        mobilux.app.config["TESTING"] = True
        self.client = mobilux.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def get(self, url, **kw):
        response = self.client.get(url, **kw)
        return response, response.get_data(as_text=True)

    def test_catalogues_have_the_same_keys(self):
        self.assertEqual(missing_keys(), {})
        self.assertEqual(set(CATALOGS["en"]), set(CATALOGS["it"]))

    def test_italian_is_default(self):
        response, html = self.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('<html lang="it">', html)
        self.assertIn("L&#39;hotel che si muove per te.", html)
        self.assertIn('hreflang="en" href="http://localhost/en/"', html)
        self.assertIn('rel="canonical" href="http://localhost/"', html)

    def test_all_pages_in_both_languages(self):
        for path in ["/", "/package/city", "/package/nature", "/book", "/my-journey"]:
            for prefix, lang in [("", "it"), ("/en", "en")]:
                response, html = self.get(prefix + path)
                self.assertEqual(response.status_code, 200, prefix + path)
                self.assertIn(f'<html lang="{lang}">', html)

    def test_templates_use_only_existing_keys(self):
        # translate() logs a warning and shows the raw key when a key is missing.
        with self.assertNoLogs("i18n", level="WARNING"):
            for path in ["/", "/package/city", "/package/nature", "/book", "/my-journey", "/nope"]:
                for prefix in ["", "/en"]:
                    self.client.get(prefix + path)
            self.client.post("/book", data={"name": "A", "email": "a@b.c", "address": "X"})
            self.client.get("/book/confirmation")

    def test_saved_preference_wins(self):
        self.client.get("/lang/en?next=/package/city")
        response = self.client.get("/package/city")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/en/package/city"))
        self.client.get("/lang/it?next=/package/city")
        self.assertEqual(self.client.get("/package/city").status_code, 200)

    def test_switch_rejects_external_redirect(self):
        response = self.client.get("/lang/en?next=//evil.example")
        self.assertTrue(response.location.endswith("/en/"))

    def test_switch_keeps_query(self):
        _, html = self.get("/book?package=nature")
        self.assertIn("/lang/en?next=/en/book?package%3Dnature", html)

    def test_booking_flow_english(self):
        response = self.client.post("/en/book", data={
            "package": "nature", "name": "Ada", "email": "ada@example.com",
            "address": "Milan", "passengers": "3", "departure_date": "2027-06-12",
            "pickup_preference": "Request home collection (subject to availability)",
            "services": ["Private guided tours", "Extra luggage requests"],
        })
        self.assertEqual(response.status_code, 302)
        _, html = self.get(response.location)
        self.assertIn("Thank you, Ada.", html)
        self.assertIn("12 June 2027", html)
        self.assertIn("Extra luggage", html)
        reference = re.search(r"MLX-\d+", html).group(0)
        # Same booking, Italian view.
        _, html_it = self.get("/book/confirmation")
        self.assertIn("12 giugno 2027", html_it)
        self.assertIn("Visite guidate private", html_it)
        # Lookup.
        html = self.client.post("/my-journey", data={"reference": reference, "email": "ada@example.com"}).get_data(as_text=True)
        self.assertIn("MOBILUX NATURE", html)

    def test_validation_messages_are_translated(self):
        html = self.client.post("/book", data={"name": "", "email": "", "address": ""}).get_data(as_text=True)
        self.assertIn("Inserisci nome, email e indirizzo di partenza.", html)
        html = self.client.post("/en/my-journey", data={"reference": "x", "email": "y@z"}).get_data(as_text=True)
        self.assertIn("No demonstration booking found.", html)

    def test_legacy_service_values_display(self):
        with mobilux.connect() as db:
            db.execute("INSERT INTO bookings (reference, package, departure_date, passengers, customer_name, email,"
                       " pickup_address, pickup_preference, services, notes, created_at) VALUES"
                       " ('MLX-1','MOBILUX CITY','',1,'A','a@b.c','X','Nearest designated pick-up point',"
                       "'Something old, Special celebrations','','2026-01-01 10:00')")
        html = self.client.post("/my-journey", data={"reference": "MLX-1", "email": "a@b.c"}).get_data(as_text=True)
        self.assertIn("Something old", html)
        self.assertIn("Ricorrenze e occasioni speciali", html)
        self.assertIn("Da concordare", html)

    def test_404_localized(self):
        response, html = self.get("/en/nope")
        self.assertEqual(response.status_code, 404)
        self.assertIn("This page does not exist", html)
        response, html = self.get("/nope")
        self.assertIn("Questa pagina non esiste", html)

    def test_sitemap_and_robots(self):
        response, xml = self.get("/sitemap.xml")
        self.assertEqual(response.mimetype, "application/xml")
        self.assertEqual(xml.count("<url>"), 10)
        self.assertIn('hreflang="it-IT" href="http://localhost/package/city"', xml)
        _, robots = self.get("/robots.txt")
        self.assertIn("Sitemap: http://localhost/sitemap.xml", robots)

    def test_no_emoji_or_symbols_in_copy(self):
        for code, catalog in CATALOGS.items():
            for key, value in catalog.items():
                for text in (value if isinstance(value, list) else [value]):
                    self.assertIsNone(re.search(r"[–—←-⇿✀-➿\U0001F000-\U0001FFFF!]", text), (code, key))


if __name__ == "__main__":
    unittest.main()
