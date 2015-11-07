# solback.py

# Let's get this party started
import falcon
import psycopg2
import pp

class BuildingsResource(object):
    def on_get(self, req, resp):
        ip = req.env['REMOTE_ADDR']
        db = psycopg2.connect("dbname=osm user=cquest")
        cur = db.cursor()
        cur.execute("""SELECT '{"type":"Feature","properties":{"id":'|| osm_id::text
            ||',"lat":'|| round(st_y(st_centroid(geom))::numeric,6)::text
            ||',"lon":'|| round(st_x(st_centroid(geom))::numeric,6)::text
            ||',"surface":'|| round(surface::numeric)::text
            ||',"radius":'|| round(st_length(st_longestline(geom,geom)::geography)::numeric/2,1)::text
            ||'},"geometry":'|| st_asgeojson(geom,6)
            ||'}'
            FROM buildings b
            LEFT JOIN building_orient ON (osm_id=id and ip='%s')
            WHERE ST_DWithin(ST_SetSRID(ST_MakePoint(2.5,48.8),4326),geom,0.05)
            AND surface>100 AND b.orientation>0.8
            AND ip IS NULL
            ORDER BY random() LIMIT 1;""" % ip
        )
        building = cur.fetchone()

        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status
        resp.set_header('X-Powered-By', 'OpenSolarMap')
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Headers', 'X-Requested-With')
        resp.body = (building[0])
        db.close()

    def on_post(self, req, resp):
        db = psycopg2.connect("dbname=osm user=cquest")
        cur = db.cursor()
        id=int(req.params['id'])
        type=int(req.params['type'])
        ip=req.env['REMOTE_ADDR']
        cur.execute(
            """INSERT INTO building_orient (id, orientation, time, ip) VALUES (%s, %s, NOW(), %s);""",
            (id,type,ip)
        )
        db.commit()
        cur.close()
        db.close()


# falcon.API instances are callable WSGI apps
app = falcon.API()

# Resources are represented by long-lived class instances
buildings = BuildingsResource()

# things will handle all requests to the '/things' URL path
app.add_route('/building', buildings)
