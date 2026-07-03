import requests

path = "https://phl.carto.com/api/v2/sql?q=SELECT * FROM incidents_part1_part2 LIMIT 5"

response = requests.get(path)
if response.status_code == 200:
    data = response.json()
    # convert the data to a pandas DataFrame
    import pandas as pd
    df = pd.DataFrame(data['rows'])
    print(df)
    print(df.info())