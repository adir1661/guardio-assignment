## Poke'mon Reverse Proxy - Guardio Home Assignment

install dependencies (on mac or linux): 
```
python -m virtualenv venv

source ./venv/bin/activate

python -m pip install pip-tools

python -m piptools sync requirements.txt 
```

add `POKESECRET_KEY` as the secret key, and `POKEPROXY_CONFIG` to the config file location.

run the server:
```
source .env
python main.py
```


publish server (will serve also https requests): 
```
brew install ngrok

// create ngrok account 

ngrok http http://0.0.0.0:8000
```

afterward store the url of the ngrok server in the format  `https://<xxxxx>.ngrok-free.app` for later

to stream the pokemon streamer run:
```
curl -X POST https://hiring.external.guardio.dev/be/stream_start \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://<xxxxx>.ngrok-free.app/stream",
    "email": "test@guard.io",
    "enc_secret": "<secret encoded>" 
}'
```


### extras: 
to encrypt the secret run:
```
echo "<secret>" | base64 
```

test application:
```
pytest test_main.py
```

working example `.env`: 
```
POKEPROXY_CONFIG=./routes_config.json
POKESECRET_KEY=default_key

DEBUG=true
```