# solback.py

import falcon
import psycopg2
import uuid

class BuildingsResource(object):
    def getBuilding(self, req, resp):
        db = psycopg2.connect("dbname=osm user=cquest")
        cur = db.cursor()
        ip = req.env['REMOTE_ADDR']
        # get a building from the allready partially crowdsourced ones
        query = """SELECT '{"type":"Feature","properties":{"id":'|| osm_id::text
            ||',"lat":'|| round(st_y(st_centroid(geom))::numeric,6)::text
            ||',"lon":'|| round(st_x(st_centroid(geom))::numeric,6)::text
            ||',"surface":'|| round(surface::numeric)::text
            ||',"radius":'|| round(st_length(st_longestline(geom,geom)::geography)::numeric/2,1)::text
            ||'},"geometry":'|| st_asgeojson(geom,6) ||'}'
            FROM building_next n
            LEFT JOIN building_orient o ON (o.id=n.id and o.ip='%s')
            JOIN buildings b ON (b.osm_id=n.id)
            WHERE n.total<10 AND o.ip is null
            GROUP BY b.osm_id, b.geom, b.surface, n.nb, n.last, b.orient_type
            HAVING orient_type is null
            ORDER BY n.nb desc, n.last limit 1;""" % (ip)
        cur.execute(query)

        if cur.rowcount == 0:
            # get one random building around our location
            default_lat = '44.1'
            default_lon = '4.8'
            lat = float(req.params.get('lat',default_lat))
            lon = float(req.params.get('lon',default_lon))
            if (lat == float(default_lat)):
                order = "n.nb DESC, n.last, b.orientation DESC"
            else:
                order = "ST_Distance(geom,ST_SetSRID(ST_MakePoint(%s,%s),4326))/(coalesce(n.nb,0)*10+1)" % (lon,lat)
            query = """SELECT '{"type":"Feature","properties":{"id":'|| osm_id::text
                ||',"lat":'|| round(st_y(st_centroid(geom))::numeric,6)::text
                ||',"lon":'|| round(st_x(st_centroid(geom))::numeric,6)::text
                ||',"surface":'|| round(surface::numeric)::text
                ||',"radius":'|| round(st_length(st_longestline(geom,geom)::geography)::numeric/2,1)::text
                ||'},"geometry":'|| st_asgeojson(geom,6)
                ||'}'
                FROM buildings b
                LEFT JOIN building_orient o1 ON (osm_id=o1.id and o1.ip='%s')
                LEFT JOIN building_orient o2 ON (osm_id=o2.id)
                LEFT JOIN building_next n ON (n.id=b.osm_id AND n.nb>=0)
                WHERE ST_DWithin(ST_SetSRID(ST_MakePoint(%s,%s),4326),geom,0.1)
                AND surface>100 AND b.orientation>0.8 AND b.orient_type IS NULL
                AND coalesce(n.total,0)<10 AND o1.ip IS NULL
                GROUP by osm_id, geom, surface, b.orientation, n.nb, n.last
                HAVING (count(o2.*)<10 or (count(distinct(o2.orientation))=1 AND count(o2.*)<=3))
                ORDER BY %s LIMIT 1;""" % (ip,lon,lat,order)
            cur.execute(query)
        building = cur.fetchone()

        # cookie management
        cookies = req.cookies
        if "opensolar_user" in cookies:
            my_cookie_value = cookies["opensolar_user"]
        else:
            resp.set_cookie("opensolar_user", str(uuid.uuid1()), path=".opensolarmap.org", secure=False, http_only=False)
        resp.status = falcon.HTTP_200
        resp.set_header('X-Powered-By', 'OpenSolarMap')
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Headers', 'X-Requested-With')
        try:
            resp.body = (building[0])
        except:
            print("no building")
        db.close()

    def on_get(self, req, resp):
        self.getBuilding(req, resp);

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
        self.getBuilding(req, resp);

class StatsResource(object):
    def on_get(self, req, resp):
        ip = req.env['REMOTE_ADDR']
        db = psycopg2.connect("dbname=osm user=cquest")
        cur = db.cursor()
        cur.execute("SELECT count(*) from building_orient where ip = '%s';" % ip)
        stat = cur.fetchone()
        count_ip = stat[0]
        cur.execute("SELECT count(*) from building_orient;")
        stat = cur.fetchone()
        count_total = stat[0]
        cur.execute("SELECT count(distinct(ip)) from building_orient;")
        stat = cur.fetchone()
        count_ips = stat[0]
        cur.execute("SELECT count(distinct(id)) from building_orient;")
        stat = cur.fetchone()
        count_buildings = stat[0]
        cur.close()
        db.close()

        resp.body = """{"count_total":%s,"count_ip":%s,"count_ips":%s,"count_buildings":%s}""" % (count_total, count_ip, count_ips, count_buildings)
        resp.set_header('X-Powered-By', 'OpenSolarMap')
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Headers', 'X-Requested-With')
        resp.status = falcon.HTTP_200

# falcon.API instances are callable WSGI apps
app = falcon.API()

# Resources are represented by long-lived class instances
buildings = BuildingsResource()
stats = StatsResource()

# things will handle all requests to the matching URL path
app.add_route('/building', buildings)
app.add_route('/stats', stats)

