"""
A tiny test program, which shows how to use the VciderApiClient.

"""
from api_client import VciderApiClient

#
# Provide these three values...
#
APP_ID  = "0"
API_ID  = "59a7b4173e3254c0b4e222bf60b31136"    # Your public API-ID.
API_KEY = "a775b5a5c19856a1acff88da7db72cc2"    # Your secret API access key. Please keep secret!
ROOT    = "http://localhost:8000"               # The vCider API server's root URI.


vac = VciderApiClient(ROOT, API_ID, API_KEY)

vac.time_sync()                                 # Only needed when client/server clocks are off

r = vac.get("/api/root/")
print r.content


