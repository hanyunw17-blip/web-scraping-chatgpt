import sys
from pathlib import Path
import csv

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
LIB_DIR = ROOT_DIR / "vendor"
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from gps import Sort, reviews  # noqa: E402

appid = "com.openai.chatgpt"
maxDataSize = 1000

result, continuation_token = reviews(
    appid,
    lang='en',
    country='us',
    sort=Sort.NEWEST,
    count=maxDataSize,
)

if continuation_token:
    more_result, _ = reviews(
        appid,
        continuation_token = continuation_token
    )
    result.extend(more_result)
data_list = []
for data in result:
    data_dict = {
        'name': data.get('userName'),
        'content': data.get('content'),
        'score': data.get('score'),
        'at': data.get('at'),
        'appversion': data.get('appVersion'),
    }
    data_list.append(data_dict)

if not data_list:
    print('No review data retrieved')
else:
    output_path = OUTPUT_DIR / f'{appid}.csv'
    with output_path.open('w', encoding='utf-8-sig', newline='') as f:
        title = data_list[0].keys()
        writer = csv.DictWriter(f, title)
        writer.writeheader()
        writer.writerows(data_list)
    print('CSV file has been written')