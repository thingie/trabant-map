#!/usr/bin/python

from werkzeug.wrappers import Response, Request
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
import simplejson
import datetime
import re
import logging

from libtm.markingpoint import MarkingPoint
from libtm.datasource import PointSqliteDatabase

class TrabantConfig(object):
    def __init__(self, config):
        if 'remarkLimit' in config:
            self.remarkLimit = int(config['remarkLimit'])
            logging.info('remarkLimit set to %d', self.remarkLimit)
        else:
            self.remarkLimit = 1024
            logging.info('remarkLimit defaults to %d', self.remarkLimit)

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

        self.config = TrabantConfig(config)
        self.points = PointSqliteDatabase({'sqlfile': 'cars.db'})
        logging.debug('TrabantMap instatiated')

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            logging.debug('Request on_%s', endpoint)
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
        logging.debug('static file "%s", mimetype=%s', resource, mimetype)
        return Response(source.read(), mimetype=mimetype)

    def on_root_map(self, request):
        return self.on_static_get(request, resource='map.html')

    def on_car_map(self, request):
        cars = self.points.getPoints(ptype='car')
        jsonCars = []
        for i in cars:
            jsonCars.append(i.toJson())

        return Response(simplejson.dumps(jsonCars), mimetype='text/json')

    def on_new_item(self, request):
        valid = true
        try:
            latitude = float(request.form.get('lat'))
            longitude = float(request.form.get('lon'))
            remark = request.form.get('remark')

            if latitude < -90 or latitude > 90:
                valid = false
            if longitude < -180 or longitude > 180:
                valid = false

            if len(remark) > self.config.remarkLimit:
                valid = false
        except Exception, e:
            valid = false

        if not valid:
            return Response(simplejson.dumps(['FAIL', 'invalid input']), mimetype='text/json')

        mp = MarkingPoint()
        try:
            mp.lat = latitude
            mp.lon = longitude
            mp.remark = remark
            mp.ptype = 'car'
            self.points.addPoint(mp)
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
