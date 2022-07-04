#!/bin/sh

until pg_isready -h $POSTGRESQL_HOST -U $POSTGRES_USER -d $POSTGRES_DB; do
    echo "Waiting for postgres server, $POSTGRESQL_HOST $POSTGRES_USER $POSTGRES_DB"
    sleep 1;
done