import datetime

class MarkingPoint(object):
    def __init__(self, lat=0, lon=0, remark=None, ptype=None):
        self.id = None
        self.createTime = datetime.datetime.now()
        self.lat = lat
        self.lon = lon
        self.remark = remark
        self.ptype = ptype
        self.enabled = 1

    def toJson(self):
        return {
            'createTime': self.createTime.isoformat() if self.createTime is not None else '',
            'lat': self.lat,
            'lon': self.lon,
            'remark': self.remark if self.remark is not None else '',
            'id': self.id if self.id is not None else -1,
            'ptype': self.ptype if self.ptype is not None else '',
            'enabled': self.enabled,
        }
