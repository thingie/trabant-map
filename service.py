#!/usr/bin/python

from werkzeug.wrappers import Response, Request
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
import simplejson
import datetime
import re
import logging
from jinja2 import Template, Environment, FileSystemLoader

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
            Rule('/admin/disable', endpoint='point_disable'),
            Rule('/admin/enable', endpoint='point_enable'),
            Rule('/static/<string:resource>', endpoint='static_get'),
        ])

        self.config = TrabantConfig(config)
        self.points = PointSqliteDatabase({'sqlfile': 'points.db'})
        self.jinjaenv = Environment(loader=FileSystemLoader('templates/'))
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
        elif re.match('.*.css$', resource):
            mimetype = 'text/css'
        logging.debug('static file "%s", mimetype=%s', resource, mimetype)
        return Response(source.read(), mimetype=mimetype)

    def on_root_map(self, request):
        return self.on_static_get(request, resource='map.html')

    def getPoints(self, ptype):
        points = self.points.getPoints(ptype=ptype)
        return Response(
            simplejson.dumps([x.toJson() for x in points]),
            mimetype='text/json')

    def on_car_map(self, request):
        return self.getPoints('car')

    def on_shop_map(self, request):
        return self.getPoints('shop')

    def on_club_map(self, request):
        return self.getPoints('club')

    def on_part_map(self, request):
        return self.getPoints('part')

    def on_new_item(self, request):
        valid = True
        try:
            latitude = float(request.form.get('lat'))
            longitude = float(request.form.get('lon'))
            remark = request.form.get('remark')
            ptype = request.form.get('ptype') or 'car'

            if latitude < -90 or latitude > 90:
                logging.info('latitude %f is invalid', latitude)
                valid = False
            if longitude < -180 or longitude > 180:
                logging.info('longitude %f is invalid', longitude)
                valid = False

            if len(remark) > self.config.remarkLimit:
                logging.info('remark is too long')
                valid = False

            if ptype not in ('car', 'shop', 'part', 'club'):
                logging.info('invalid ptype "%s"', ptype)
                valid = False

        except Exception, e:
            logging.warning('validation error: %s', e)
            valid = False

        if not valid:
            return Response(simplejson.dumps(['FAIL', 'invalid input']), mimetype='text/json')

        mp = MarkingPoint()
        try:
            mp.lat = latitude
            mp.lon = longitude
            mp.remark = remark
            mp.ptype = ptype
            self.points.addPoint(mp)
        except Exception, e:
            return Response(simplejson.dumps(['FAIL', str(e)]), mimetype='text/json')
        return Response(simplejson.dumps(['OK', mp.toJson()]), mimetype='text/json')

    def on_admin(self, request):
        ptype = request.form.get('ptype') or None

        page = 1
        pageTotal = 1

        typeCount = self.points.getPointCount(ptype=ptype)
        points = self.points.getPoints(ptype=ptype, disabled=True)

        template = self.jinjaenv.get_template('admin.html')
        data = {
            'itemTotal': typeCount,
            'page': page,
            'pageTotal': pageTotal,
            'points': points,
        }
        return Response(template.render(data), mimetype='text/html')

    def on_point_enable(self, request):
        itemId = request.args.get('id') or None
        if itemId is None:
            return Response(simplejson.dumps(['FAIL', 'invalid input']),
                            mimetype='text/json')

        try:
            self.points.changePoint(int(itemId), 'enable')
        except Exception, e:
            return Response(simplejson.dumps(['FAIL', 'query failed']),
                            mimetype='text/json')
            

        return Response(simplejson.dumps(['OK']),
                        mimetype='text/json')
        
    def on_point_disable(self, request):
        itemId = request.args.get('id') or None
        if itemId is None:
            return Response(simplejson.dumps(['FAIL', 'invalid input']),
                            mimetype='text/json')

        try:
            self.points.changePoint(int(itemId), 'disable')
        except Exception, e:
            return Response(simplejson.dumps(['FAIL', 'query failed']),
                            mimetype='text/json')

        return Response(simplejson.dumps(['OK']),
                        mimetype='text/json')
        
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
