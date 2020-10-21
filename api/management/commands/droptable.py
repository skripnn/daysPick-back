from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Drop table'

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

        t = "DROP TABLE simple_email_confirmation_emailaddress;"
        print("ok")
        db_cursor.execute(t)
        db_cursor.close()

        psql_con.close()

