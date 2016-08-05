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

# update orientation in the backend database based on contributions...
cur.execute("""
with u as (select c1.id as u_id, c1.orientation as u_orient
	from building_contribs c1
	left join building_contribs c2 on (c2.id=c1.id and c2.rank>1)
	where c1.rank=1 and c1.nb>=3
	group by c1.id, c1.orientation, c1.nb, c1.rank, c1.first, c1.last
	having c1.nb-coalesce(sum(c2.nb),0)>=3)
update buildings set orient_type=u_orient
	from u where osm_id=u_id and orient_type is null;
""")
# mark these buildings as done
cur.execute("""
with u as (select osm_id from buildings where orient_type is not null)
update building_orient set done=true
	from u
	where id=osm_id and done is null;
""")

# get data to upload to OSM API
query = """with i as (select nom as c_name, insee as i_insee , count(*) as nb from communes c join buildings b on (st_intersects(c.wkb_geometry, b.geom))
    where osm_id>0 AND orient_type in (1,2,3) GROUP BY 1,2 ORDER BY 3 DESC LIMIT 1)
    select osm_id, insee, c_name, orient_type, st_width(geom), st_height(geom) as h from communes c join i on (c.insee=i_insee)
      join buildings b on (st_intersects(c.wkb_geometry, b.geom))
      where osm_id>0 AND orient_type in (1,2,3);"""
cur.execute(query)
print(cur.rowcount)
for building in cur:
  way_id = building[0]
  orientation = building[3]
  building_w = building[4]
  building_h = building[5]

  tag = None
  if orientation == 1:
      if building_w/building_h > 1.2:
          tag = 'along'
      elif building_h/building_w > 1.2:
          tag = 'across'
      else:
          continue
  if orientation == 2:
      if building_w/building_h > 1.2:
          tag = 'across'
      elif building_h/building_w > 1.2:
          tag = 'along'
      else:
          continue

  if tag is not None or orientation == 3:
      if commune == "":
          api.ChangesetCreate({u"comment": u"roof orientation crowdsourced on OpenSolarMap - %s (%s)" % (building[2],building[1])})
          commune = building[2]
          print(building)
      try:
          way = api.WayGet(way_id)
          tags = way['tag']
          if orientation == 3:
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
          elif tag is not None:
              orient = tags.get('roof:orientation','')
              if orient == '':
                  # add roof:orientation=along/across tag to way
                  tags['roof:orientation']=tag
                  if orientation==1:
                      tags['roof:orientation:compass']='N-S'
                  if orientation==2:
                      tags['roof:orientation:compass']='E-W'
                  way['tag']=tags
                  # update way on OSM API
                  api.WayUpdate(way)
                  orient = tag
              if orient == tag:
                  # update local building data
                  sqlupdate.execute("""UPDATE buildings SET orient_type=-%s WHERE osm_id = %i;""" % (orientation, way_id))

      except:
          pass

db.close()
