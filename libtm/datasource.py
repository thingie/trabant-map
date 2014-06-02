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

    def changePoint(self, itemId, action):
        if action not in ('enable', 'disable'):
            raise Exception("invalid action")
        newState = 1 if action == 'enable' else 0

        try:
            self.dblock.acquire()
            query = "UPDATE points SET enabled=? WHERE id=?"

            logging.debug("QUERY: %s", query)
            c = self.sqlite.cursor()
            c.execute(query, (newState, itemId))
            self.sqlite.commit()
            c.close()
        except Exception, e:
            logging.error('Failed to query the db: %s', e)
            raise Exception("failed to read db")
        finally:
            self.dblock.release()

    def getPointCount(self, boundingBox=None, ptype=None):
        """
        Check how many points of the given type and bounding box are there
        """
        self.dblock.acquire()
        try:
            query = "SELECT COUNT(1) FROM points"
            queryLimit = []
            queryData = []

            if ptype is not None:
                queryLimit.append(" ptype=? ")
                queryData.append(ptype)

            if boundingBox is not None:
                if len(boundingBox) != 4 or \
                   not all(type(i) == float for i in boundingBox):
                    raise Exception("Invalid bounding box")
                queryLimit.append(" lat > ? AND lon > ? AND lat < ? AND lon < ? ")

            if len(queryLimit):
                query += " WHERE " + " AND ".join(queryLimit)

            logging.debug("QUERY: %s", query)
            c = self.sqlite.cursor()
            c.execute(query, queryData)

            i = c.fetchone()
            return i[0]
            c.close()
        except Exception, e:
            logging.error('Failed to query the db: %s', e)
            raise Exception("failed to read db")
        finally:
            self.dblock.release()

        return 0

    def getPoints(self, boundingBox=None, ptype=None, disabled=False, limit=None, limitOffset=None):
        """
        Get points from the database

        Optional constraints are:
          boundingBox, tuple of exactly 4 ints
          ptype, str
          disabled, set true to get the disabled points as well
          limit, how many rows
          limitOffset, offset for limit
        """
        self.dblock.acquire()
        points = []
        try:
            query = "SELECT createTime, lat, lon, remark, id, ptype, enabled FROM points"
            limits = []
            queryData = []

            if not disabled: # not asking for disabled items
                limits.append(" enabled=1 ")

            if ptype is not None:
                limits.append(" ptype=? ")
                queryData.append(ptype)

            if boundingBox is not None:
                if len(boundingBox) != 4 or \
                   not all(type(i) == float for i in boundingBox):
                    raise Exception("Invalid bounding box")
                limits.append(" lat > ? AND lon > ? AND lat < ? AND lon < ? ")
                queryData.append(boundingBox)

            if len(limits):
                query += " WHERE " + " AND ".join(limits)

            if limit is not None:
                query += " LIMIT ? "
                queryData.append(limit)
                if limitOffset is not None:
                    query += " OFFSET ? "
                    queryData.append(limitOffset)

            logging.debug("QUERY: %s", query)
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
                point.enabled = i[6]

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
