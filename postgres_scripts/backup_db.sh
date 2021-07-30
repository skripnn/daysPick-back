#!/bin/bash

#export PGPASSWORD=$POSTGRES_PASSWORD
pg_dump -w --username=postgres --dbname=postgres > backup.sql