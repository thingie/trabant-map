"""
Database connector
"""

from markingpoint import MarkingPoint
import sqlite3
import threading
import logging

class PointSqliteDatabase(object):
    def __init__(self, config=None):
        logging.info('initiating d from %s', config['sqlfile'])
        if config is not None:
            self.sqlite = sqlite3.connect(config['sqlfile'],
                                          detect_types=sqlite3.PARSE_DECLTYPES,
                                          check_same_thread=False)
            logging.info('opened db from file: %s', config['sqlfile'])
        else:
            raise Exception("no config provided for the database")

        self.dblock = threading.Lock()

    def getPoints(self, boundingBox=None, ptype=None):
        self.dblock.acquire()
        points = []
        try:
            query = "SELECT createTime, lat, lon, remark, id, ptype FROM points WHERE enabled=1"
            queryData = []

            if ptype is not None:
                query += " AND ptype=?"
                queryData.append(ptype)

            if boundingBox is not None:
                assert len(boundingBox) == 4
                query += " AND lat > ? AND lon > ? AND lat < ? AND lon < ?"
                query += queryData.append(boundingBox)

            c = self.sqlite.cursor()
            c.execute(query, queryData)

            i = c.fetchone()
            while i is not None:
                point = MarkingPoint()
                point.createTime = i[0]
                point.lat = i[1]
                point.lon = i[2]
                point.remark = i[3]
                point.id = i[4]
                point.ptype = i[5]

                points.append(point)
                i = c.fetchone()
            c.close()
        except Exception, e:
            logging.error('Failed to query the db: %s', e)
            raise Exception("failed to read db")
        finally:
            self.dblock.release()

        return points

    def addPoint(self, markingPoint):
        logging.info('Creating new point %r', markingPoint)
        try:
            self.dblock.acquire()
            c = self.sqlite.cursor()
            c.execute("INSERT INTO points (lat, lon, remark, createTime, enabled, ptype) VALUES (?, ?, ?, ?, 1, ?)",
                      (markingPoint.lat, markingPoint.lon, markingPoint.remark, markingPoint.createTime,
                       markingPoint.ptype))
            self.sqlite.commit()
            c.close()
            return True
        except Exception, e:
            logging.error('Failed to create a point: %s', e)
            raise Exception("Failed to add a car: %s" % e)
        finally:
            self.dblock.release()
