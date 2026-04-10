import urllib.request

data = open('../drive1.csv', 'rb').read()
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="drive1.csv"\r\n'
    f'Content-Type: text/csv\r\n\r\n'
).encode('utf-8') + data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

req = urllib.request.Request('http://127.0.0.1:8080/api/upload', data=body)
req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(e.read().decode())
