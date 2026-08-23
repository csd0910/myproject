import urllib.request, urllib.error
req = urllib.request.Request('https://task-mining-server-1097969102143.asia-northeast1.run.app/api/dashboard/user_data?user_id=ALL', headers={'User-Agent': 'Mozilla/5.0'})
try:
    print(urllib.request.urlopen(req).read().decode('utf-8')[:200])
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode("utf-8")}')
