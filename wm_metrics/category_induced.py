#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Compute the induced Category of a Category.

Induced category of a category C is a category created to describe
images of category C.
"""

import mw_api
import mw_util
import json
import MySQLdb
import operator
import sys
from _mysql_exceptions import OperationalError

reload(sys)
sys.setdefaultencoding("utf-8")


class DatabaseException(Exception):
    pass


class CategoryInduced:

    def __init__(self, category):
        url_api = 'https://commons.wikimedia.org/w/api.php'
        self.commons = mw_api.MwWiki(url_api=url_api)
        self.category = category.replace(" ", "_").decode('utf-8')
        self.categories = []
        self.first_images = []
        self.init_database_connection()
        # TODO: prendre que des images
        self.query = """SELECT page.page_title
                        FROM page
                        JOIN categorylinks ON page.page_id = categorylinks.cl_from
                        WHERE categorylinks.cl_to = %s AND categorylinks.cl_type = "file"
                        ORDER BY categorylinks.cl_timestamp ASC
                        LIMIT 1;"""

    def init_database_connection(self):
        """Initialise the connection to the database."""
        try:
            host = "commonswiki.labsdb"
            self.db = MySQLdb.connect(host=host,
                                      db="commonswiki_p",
                                      read_default_file="~/replica.my.cnf",
                                      charset='utf8')
            self.cursor = self.db.cursor()
        except OperationalError:
            raise DatabaseException("Could not connect to host %s" % host)

    def list_category(self):
        """ Returns List categories inside self.category. """
        result = None
        res = []
        lastcontinue = ""
        props = {
            "prop": "categories",
            "cllimit": "max",
            #          "cldir" : "ascending",
            "generator": "categorymembers",
            "gcmtitle": self.category,
            "gcmprop": "title",
            "gcmlimit": 20
        }
        while True:
            result = json.loads(
                self.commons.send_to_api(mw_api.MwApiQuery(properties=props)))
            dic = result[u'query'][u'pages']
            list = sorted(
                dic.iteritems(), reverse=False, key=operator.itemgetter(1))
            liste2 = [x[1][u'categories']
                      for x in list if u'categories' in x[1].keys()]
            for l in liste2:
                categories = [x[u'title'] for x in l]
                res.extend(categories)
            if 'query-continue' in result.keys() and 'categorymembers' in result['query-continue'].keys():
                lastcontinue = result['query-continue']['categorymembers']
                self.update(props, lastcontinue)
            else:
                break
        return set(res)

    def first_image(self, category):
        self.catsql = category.replace("Category:", "").replace(" ", "_")
        self.cursor.execute(self.query, self.catsql)
        cat_content = self.catsql.encode('utf-8')
        first_content = [x[0].decode('utf-8') for x in self.cursor.fetchall()]
        res = [cat_content, first_content]
        return res

    def list_images(self):
        list = []
        lastContinue = ""
        props = {
            "list": "categorymembers",
            "cmtitle": self.category,
                    "cmprop": "title",
                    "cmlimit": "max",
        }
        while True:
            result = json.loads(
                self.commons.send_to_api(mw_api.MwApiQuery(props)))
            res1 = [x[u'title'] for x in result[u'query'][u'categorymembers']]
            res = [x.encode('utf-8') for x in res1]
            list.extend(res)
            if 'query-continue' in result.keys() and 'categorymembers' in result['query-continue'].keys():
                lastContinue = result['query-continue']['categorymembers']
                self.update(props, lastContinue)
            else:
                break
        return list

    def update(self, props, lastContinue):
        for p in lastContinue:
            props[p] = lastContinue[p]

    def induce_categories(self):
        self.categories = self.list_category()
        first_images = [self.first_image(x) for x in self.categories]
        first_images.sort()
        self.images = [x.decode('utf-8')[5:].replace(" ", "_") for x in self.list_images()]
        self.images_count = len(self.images)
        self.result = [first_images[x][0] for x in range(len(first_images))
                       if (len(first_images[x][1]) > 0
                           and first_images[x][1][0] in self.images)]
        self.result.sort()
        self.results_count = len(self.result)
        self.categories_traversed_count = len(first_images)

    def print_report(self):
        print "--------------------first images--------------------"
        print "%s categories to check" % self.categories_traversed_count
        print "----------------------images------------------------"
        print "%s images" % self.images_count
        print "----------------------result------------------------"
        print "%s new categories created" % self.results_count
        print self.result


def main():
    from argparse import ArgumentParser
    description = "Computes metrics about a commons category"
    parser = ArgumentParser(description=description)
    parser.add_argument("-c", "--category",
                        type=str,
                        dest="category",
                        metavar="CAT",
                        required=True,
                        help="The category on which we compute metrics")
    args = parser.parse_args()
    category = mw_util.str2cat(args.category)
    ci = CategoryInduced(category)
    ci.induce_categories()
    ci.print_report()


if __name__ == "__main__":
    main()
