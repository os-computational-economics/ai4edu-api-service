#!/bin/sh

SERVERS_JSON_PATH="/pgadmin4/servers.json"
PGPASSFILE="$HOME/.pgpass"

# Create the .pgpass file for password
echo "Creating pgpass file at $PGPASSFILE"
echo "${POSTGRES_ENDPOINT}:*:*:${POSTGRES_USER}:${POSTGRES_PASSWORD}" > "$PGPASSFILE"
chmod 600 $PGPASSFILE
cat $PGPASSFILE
echo "pgpass file created successfully."

echo "Creating servers.json file in $SERVERS_JSON_PATH"
# Substitute placeholders in the template file using sed
sed \
  -e "s|\${POSTGRES_ENDPOINT}|${POSTGRES_ENDPOINT}|g" \
  -e "s|\${POSTGRES_DB}|${POSTGRES_DB}|g" \
  -e "s|\${POSTGRES_USER}|${POSTGRES_USER}|g" \
  -e "s|\${PGPASSFILE}|${PGPASSFILE}|g" \
  /pgadmin_init/servers.json.template > "$SERVERS_JSON_PATH"

echo "$SERVERS_JSON_PATH file created successfully."
cat $SERVERS_JSON_PATH

echo "Starting pgAdmin4..."
exec /entrypoint.sh
echo "pgAdmin4 started."