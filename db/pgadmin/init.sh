#!/bin/sh

export PGPASSFILE="$HOME/.pgpass"

# Create the .pgpass file for password
echo "Creating pgpass file at $PGPASSFILE"
echo "${PGPASS}" > "$PGPASSFILE"
chmod 600 $PGPASSFILE
echo "pgpass file created successfully."

envsubst '${POSTGRES_ENDPOINT} ${POSTGRES_DB} ${POSTGRES_USER} ${PGPASSFILE}' < /pgadmin4/servers.json.template > /pgadmin4/servers.json
echo "servers.json file created successfully."

echo "Starting pgAdmin4..."
exec /entrypoint.sh
echo "pgAdmin4 started."
