// markers to be displayed on the map
var markers = [];

// marker for a new item 
var newmarker = L.marker([0, 0]);
function hideNewMarker(e) {
    map.removeLayer(newmarker);
    document.getElementById('newPointForm').style.display = 'none';
    document.getElementById("form-remark").value = '';

};
newmarker.on('click', hideNewMarker);

// some utility functions
function pointDebug(point) {
    var str = '{\n';
    str += 'lat:' + point.lat + ',\n';
    str += 'lon:' + point.lon + ',\n';
    str += 'id:' + point.id + ',\n';
    str += 'remark:' + point.remark + ',\n';
    str += 'createTime:' + point.createTime + ',\n';
    str += '}\n';
    return str;
};

function getTypeFromHash() {
    if (location.hash != '') {
        var h = location.hash.substring(1);
        var itemType = h.split('&')[0];

        return itemType;
    } else {
        return 'cars';
    }
};

var lohash = location.hash.substr(1);
var zoom = lohash.substr(lohash.indexOf('z=')).split('&')[0].split('=')[1];
var lat = lohash.substr(lohash.indexOf('lat=')).split('&')[0].split('=')[1];
var lon = lohash.substr(lohash.indexOf('lon=')).split('&')[0].split('=')[1];

if (!zoom) {
    zoom = 11;
}
if (!lat) {
    lat = 50.0792;
}
if (!lon) {
    lon = 14.4032;
}

var map = L.map('map').setView([lat, lon], zoom);
L.tileLayer('https://{s}.tiles.mapbox.com/v3/pinkpony.i9mae5c5/{z}/{x}/{y}.png', {
    attribution: 'map data &copy; mapbox.com',
    maxZoom: 18
}).addTo(map);

function mapDragHandler(e) {
    location.hash = '#' + getTypeFromHash() + '&z=' + map.getZoom() + '&lat=' + map.getCenter().lat +
        '&lon=' + map.getCenter().lng;
};
map.on('move', mapDragHandler);

// adding new markers 
function addNewClick(e) {
    document.getElementById('newPointForm').style.display = 'block';
    document.getElementById('form-lat').value = e.latlng.lat;
    document.getElementById('form-lon').value = e.latlng.lng;
    
    newmarker.setLatLng(e.latlng);
    newmarker.addTo(map);
}
map.on('click', addNewClick);

var itemType = '/cars';
if (getTypeFromHash() == 'shops') {
    itemType = '/shops';
} else if (getTypeFromHash() == 'clubs') {
    itemType = '/clubs';
} else if (getTypeFromHash() == 'parts') {
    itemType = '/parts';
}

var myr = new XMLHttpRequest();
myr.open('get', itemType, false);
myr.onload = function() {
    var mymarkers = JSON.parse(this.responseText);
    for (var i = 0; i < mymarkers.length; i++) {
        markers.push(mymarkers[i]);
    }
};
myr.send();

function showDetails(e) {
    this['marker'].openPopup();
}

function addMarker(data) {
    var nm = L.marker([data.lat, data.lon]);
    nm.bindPopup('<h2>' + data.remark + '</h2><p class="detail">' + data.createTime + ' (id:' + data.id + ')</p>');
    nm.on('click', showDetails, {'data': data, 'marker': nm});
    nm.addTo(map);
}

for (var i = 0; i < markers.length; i++) {
    addMarker(markers[i]);
}

function sendNewItem() {
    var ok = false;
    var r = new XMLHttpRequest();
    var form = document.getElementById("newPointForm");
    var fdata = new FormData();
    fdata.append('lat', document.getElementById("form-lat").value);
    fdata.append('lon', document.getElementById("form-lon").value);
    fdata.append('remark', document.getElementById("form-remark").value);

    var ptype = 'car';
    var ptypeInputs = document.getElementsByName('ptype');
    for (var i = 0; i < ptypeInputs.length; i++) {
        if (ptypeInputs[i].checked == true) {
            ptype = ptypeInputs[i].value;
        }
    }

    fdata.append('ptype', ptype);

    r.onload = function(e) {
        var data = JSON.parse(this.responseText);
        if (data[0] == "OK") {
            ok = true;
            addMarker(data[1]);
        } else {
            alert("Could not add the marker, try again (or something)." + data[1]);
        }
    };
    r.open("POST", "/new", false);
    r.send(fdata);

    if (ok) {
        map.removeLayer(newmarker);
        document.getElementById('newPointForm').style.display = 'none';
        document.getElementById("form-remark").value = '';

        // if we added a point of another type than is currently displayed
        // we must hide it (but this is a bad design, in future, we won't
        // allow it -- TODO
    }
}
document.getElementById('npSend').onclick = sendNewItem;
