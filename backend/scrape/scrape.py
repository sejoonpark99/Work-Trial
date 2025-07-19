import requests

payload = {
    "api_key": "12143211085ba531781f23ca0ff4cb32",
    "url": "https://www.bloomreach.com/en/case-studies",
}
r = requests.get("https://api.scraperapi.com/", params=payload)
print(r.text)
pip install git+https://github.com/browser-use/browser-use.git