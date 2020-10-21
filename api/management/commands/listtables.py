from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'List of tables'

    def handle(self, *args, **kwargs):
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        psql_con = psycopg2.connect(
            database='postgres',
            user='aleksandrneumoin',
            password='I_am_Skrip1',
            host='localhost',
            port=''
        )
        psql_con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        db_cursor = psql_con.cursor()

        s = ""
        s += "SELECT"
        s += " table_schema"
        s += ", table_name"
        s += " FROM information_schema.tables"
        s += " WHERE"
        s += " ("
        s += " table_schema = 'public'"
        s += " )"
        s += " ORDER BY table_schema, table_name;"
        db_cursor.execute(s)

        list_tables = db_cursor.fetchall()
        for t_name_table in list_tables:
            print(t_name_table[1])

        db_cursor.close()

        psql_con.close()

