### postgres windows
creo file docker compose

avvio
docker compose -f docker-compose.postgres.yml up -d

test
docker exec -it mec-postgres psql -U mec -d mec_previsioni -c "select version();"


###

*** KV
- spiegare folder input / output
- mostrare layout e previsioni
- mostrare 3 funzioni per elaborare i file da riempire
- mostrare previsioni
- i file delle rotture dove sono?
- cosa posso rimuovere perchè non serve? 

*** GENERALE
- preparare demo: storia?
- rilascio? 
- uso mio pc e poi loro?
- 
