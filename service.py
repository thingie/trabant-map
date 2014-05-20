#!/usr/bin/python

from werkzeug.wrappers import Response, Request
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
import simplejson
import datetime
import sqlite3
import re

class MarkingPoint(object):
    def __init__(self, lat=0, lon=0, remark=None):
        self.id = None
        self.createTime = datetime.datetime.now()
        self.lat = lat
        self.lon = lon
        self.remark = remark

    def toJson(self):
        return {
            'createTime': self.createTime.isoformat() if self.createTime is not None else '',
            'lat': self.lat,
            'lon': self.lon,
            'remark': self.remark,
            'id': self.id}

class CarMPDB(object):
    def __init__(self, infile):
        self.infile = infile
        
    def getAllCars(self):
        self.sqlite = sqlite3.connect(self.infile, detect_types=sqlite3.PARSE_DECLTYPES)
        query = "SELECT createTime, lat, lon, remark, id FROM cars WHERE enabled=1"
        carList = []
        c = self.sqlite.cursor()
        c.execute(query)
        i = c.fetchone()
        while i is not None:
            car = MarkingPoint()
            car.createTime = i[0]
            car.lat = i[1]
            car.lon = i[2]
            car.remark = i[3]
            car.id = i[4]
            carList.append(car)
            i = c.fetchone()
        c.close()
        return carList

    def addCar(self, car):
        self.sqlite = sqlite3.connect(self.infile, detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            c = self.sqlite.cursor()
            c.execute("INSERT INTO cars (lat, lon, remark, createTime, enabled) VALUES (?, ?, ?, ?, 1)",
                      (car.lat, car.lon, car.remark, car.createTime))
            self.sqlite.commit()
            c.close()
        except Exception, e:
            print 'failed to add a car: %s' % e
            return False
        return True
    
class TrabantMap(object):
    def __init__(self, config):
        self.url_map = Map([
            Rule('/', endpoint='root_map'),
            Rule('/cars', endpoint='car_map'),
            Rule('/shops', endpoint='shop_map'),
            Rule('/clubs', endpoint='club_map'),
            Rule('/parts', endpoint='part_map'),
            Rule('/new', endpoint='new_item'),
            Rule('/admin', endpoint='admin'),
            Rule('/static/<string:resource>', endpoint='static_get'),
        ])

        self.cars = CarMPDB('cars.db')

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except HTTPException, e:
            return e

    def on_static_get(self, request, resource=None):
        if resource is None:
            raise NotFound()
        if re.match('/', resource):
            raise NotFound()
        try:
            source = open('static/' + resource, 'r')
            # TODO -- this is completely retarded
        except Exception, e:
            raise NotFound()
        mimetype = 'octet/binary'
        if re.match('.*.html$', resource):
            mimetype = 'text/html'
        elif re.match('.*.js$', resource):
            mimetype = 'application/javascript'
        return Response(source.read(), mimetype=mimetype)

    def on_root_map(self, request):
        return self.on_static_get(request, resource='map.html')

    def on_car_map(self, request):
        cars = self.cars.getAllCars()
        jsonCars = []
        for i in cars:
            jsonCars.append(i.toJson())

        return Response(simplejson.dumps(jsonCars), mimetype='text/json')

    def on_new_item(self, request):
        mp = MarkingPoint()
        try:
            mp.lat = float(request.form.get('lat'))
            mp.lon = float(request.form['lon'])
            mp.remark = request.form['remark']
            self.cars.addCar(mp)
        except Exception, e:
            return Response(simplejson.dumps(['FAIL', str(e)]), mimetype='text/json')
        return Response(simplejson.dumps(['OK', mp.toJson()]), mimetype='text/json')

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

def create_app():
    app = TrabantMap({})
    return app
        
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()
    run_simple('127.0.0.1', 8085, app, use_reloader=True)
