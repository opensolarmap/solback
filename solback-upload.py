#!/usr/bin/env python
# solback-upload.py

import psycopg2
from osmapi import OsmApi

db = psycopg2.connect("dbname=opensolarmap")
db.autocommit = True
api = OsmApi(username = u"OpenSolarMap", passwordfile = u"./password")
cur = db.cursor()
sqlupdate = db.cursor()
commune = ""

# get data to upload to OSM API
query = """with i as (select nom as c_name, insee as i_insee , count(*) as nb from communes c join buildings b on (st_intersects(c.wkb_geometry, b.geom))
    where osm_id>0 AND orient_type=3 GROUP BY 1,2 ORDER BY 3 DESC LIMIT 1)
    select osm_id, insee, c_name from communes c join i on (c.insee=i_insee)
      join buildings b on (st_intersects(c.wkb_geometry, b.geom))
      where osm_id>0 AND orient_type=3;"""
cur.execute(query)
print(cur.rowcount)
for building in cur:
  way_id = building[0]
  if commune == "":
    api.ChangesetCreate({u"comment": u"flat roofs crowdsourced on OpenSolarMap - %s (%s)" % (building[2],building[1])})
    commune = building[2]
    print(building)
  try:
    way = api.WayGet(way_id)
    tags = way['tag']
    shape = tags.get('roof:shape','')
    if shape == '':
      # add roof:shape=flat tag to way
      tags['roof:shape']='flat'
      way['tag']=tags
      # update way on OSM API
      api.WayUpdate(way)
      shape = 'flat'
    if shape == 'flat':
      # update local building data
      sqlupdate.execute("""UPDATE buildings SET orient_type=-3 WHERE osm_id = %i;""" % (way_id))
  except:
    pass

db.close()

