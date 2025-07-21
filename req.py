import requests

# Set a cell value
response = requests.put(
    "http://127.0.0.1:5000/api/cells/A1",
    json={"value": "10"}
)
print(response.json())

# Get the cell value
response = requests.get("http://127.0.0.1:5000/api/cells/A1")
print(response.json())