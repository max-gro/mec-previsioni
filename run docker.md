# Avvio in background
docker compose -f docker-compose.postgres.yml up -d

# Stato
docker ps

# Stop e riavvio del container (i dati restano)
docker compose -f docker-compose.postgres.yml stop
docker compose -f docker-compose.postgres.yml start

# Oppure restart diretto
docker compose -f docker-compose.postgres.yml restart

# Rimozione container (i dati restano perché il volume è nominato)
docker compose -f docker-compose.postgres.yml down

# ❗ Rimozione container + VOLUME (perdi TUTTO il DB!)
docker compose -f docker-compose.postgres.yml down -v
