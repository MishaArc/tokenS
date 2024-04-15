import requests

url = "https://dextools-api.p.rapidapi.com/price/0xfb7b4564402e5500db5bb6d63ae671302777c75a"

headers = {
	"X-RapidAPI-Key": "be15d1a273msh6baf9b2d2fd4808p152447jsn54b50fdb0a71",
	"X-RapidAPI-Host": "dextools-api.p.rapidapi.com"
}

response = requests.get(url, headers=headers)

print(response.json())