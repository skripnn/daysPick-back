#!/bin/bash

psql --username=postgres --dbname=postgres --file=clear_tables.sql
psql --username=postgres --dbname=postgres --file=backup.sql
