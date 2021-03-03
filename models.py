import peewee
import argparse
import logging
from playhouse.sqlite_ext import SqliteExtDatabase

db = SqliteExtDatabase('proactions.db')

ap = argparse.ArgumentParser()
ap.add_argument("-c", "--create", action='store_true', help="create tables")
ap.add_argument("-d", "--drop", action='store_true', help="drop tables")
args = vars(ap.parse_args())

logging.basicConfig(filename='proactions.log',
                    format='%(asctime)s [%(levelname)s] - %(message)s',
                    level=logging.INFO)


class Brand(peewee.Model):

    name = peewee.TextField()
    link = peewee.TextField()

    class Meta:

        database = db
        db_table = 'brands'


class Action(peewee.Model):

    title = peewee.TextField()
    link = peewee.TextField()
    date = peewee.TextField()
    description = peewee.TextField()
    benefits = peewee.TextField()
    img = peewee.TextField(null=True)
    url_official = peewee.TextField(null=True)
    participation = peewee.TextField(null=True)
    timing = peewee.TextField(null=True)
    other_text = peewee.TextField(null=True)
    organizers = peewee.TextField(null=True)
    operators = peewee.TextField(null=True)
    rules_link = peewee.TextField(null=True)
    tags = peewee.TextField(null=True)
    comments_num = peewee.IntegerField()
    view_num = peewee.IntegerField()
    rating = peewee.TextField(null=True)

    class Meta:
        database = db
        db_table = 'actions'


class BrandAction(peewee.Model):

    brand_id = peewee.ForeignKeyField(Brand)
    action_id = peewee.ForeignKeyField(Action)

    class Meta:
        database = db
        db_table = 'brands_actions'


class Comment(peewee.Model):
    action_id = peewee.ForeignKeyField(Action, on_delete='CASCADE')
    username = peewee.TextField(null=True)
    login = peewee.TextField()
    date = peewee.TextField(null=True)
    link = peewee.TextField()
    rating = peewee.TextField(null=True)
    text = peewee.TextField()
    img = peewee.TextField(null=True)

    class Meta:
        database = db
        db_table = 'comments'


def create_tables():
    Brand.create_table()
    Action.create_table()
    BrandAction.create_table()
    Comment.create_table()


def drop_tables():
    Brand.drop_table()
    Action.drop_table()
    BrandAction.drop_table()
    Comment.drop_table()


if __name__ == '__main__':
    if args['create']:
        try:
            create_tables()
        except Exception as ex:
            logging.error(str(ex))
    if args['drop']:
        try:
            drop_tables()
        except Exception as ex:
            logging.error(str(ex))