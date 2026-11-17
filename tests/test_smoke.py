from services.weather_api import decode_wmo_code

"""
tests/test_smoke.py

Smoke test: checks that the test setup itself works before we test real features.

If this passes, we know that:
  - pytest is installed
  - pytest can find the tests/ folder
  - imports from services/ work
  - our real code can run

If this FAILS, the problem is the setup (installation, folder structure, or
imports), not the app logic. Fix that first before looking at other tests.

How to run all tests (from the project root, the beeronline folder):
    python -m pytest
"""
def test_pytest_works():
    assert decode_wmo_code(0) == "Clear sky"