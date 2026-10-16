# Flask — URL Shortener

A URL shortener with both an HTML UI and a JSON API. It stores links in SQLite,
deduplicates repeated URLs, counts clicks on every redirect and validates input.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```

Open **http://localhost:5000**.

## API

```bash
# shorten
curl -X POST localhost:5000/api/shorten -H 'content-type: application/json' \
     -d '{"url":"https://www.python.org/doc/"}'
# -> {"code":"aB3xYz","short_url":"http://localhost:5000/aB3xYz"}

# follow (302 redirect, increments clicks)
curl -i localhost:5000/aB3xYz

# stats
curl localhost:5000/api/stats/aB3xYz
```

## Concepts shown
- App-context DB connection (`flask.g`) with teardown cleanup
- Parameterized SQL (no injection)
- Collision-safe random codes generated with `secrets`
- Form handling plus a JSON API in one app

---

Portfolio reference implementation by [Zaid Mubbashar](https://github.com/ranazaid) · [zaid-mubbashar.vercel.app](https://zaid-mubbashar.vercel.app)
