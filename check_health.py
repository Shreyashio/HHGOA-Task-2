import urllib.request
r = urllib.request.urlopen('http://localhost:8000/health')
print(r.read().decode())
