# solback.py

# Let's get this party started
import falcon
import psycopg2

class BuildingsResource(object):
    def on_get(self, req, resp):
        db = psycopg2.connect("dbname=osm user=cquest")
        cur = db.cursor()
        cur.execute("""SELECT format('{"type":"Feature","properties":{"id":%s,"lat":%s,"lon":%s,"surface":%s},"geometry":%s}',
            osm_id, round(st_y(st_centroid(geom))::numeric,6), round(st_x(st_centroid(geom))::numeric,6),
            round(surface::numeric), st_asgeojson(geom,6)) FROM buildings limit 1;"""
        )
        building = cur.fetchone()

        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status
        resp.body = (building[0])


# falcon.API instances are callable WSGI apps
app = falcon.API()

# Resources are represented by long-lived class instances
buildings = BuildingsResource()

# things will handle all requests to the '/things' URL path
app.add_route('/building', buildings)

