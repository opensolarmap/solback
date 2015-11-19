--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

SET default_with_oids = false;

--
-- Name: building_orient; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE building_orient (
    id integer,
    "time" timestamp without time zone,
    orientation integer,
    ip inet
);


--
-- Name: building_contribs; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW building_contribs AS
 SELECT t.id,
    t.orientation,
    t.nb,
    t.first,
    t.last,
    rank() OVER (PARTITION BY t.id ORDER BY t.nb DESC) AS rank
   FROM ( SELECT building_orient.id,
            building_orient.orientation,
            count(*) AS nb,
            min(building_orient."time") AS first,
            max(building_orient."time") AS last
           FROM building_orient
          GROUP BY building_orient.id, building_orient.orientation) t;


--
-- Name: building_next; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW building_next AS
 SELECT c1.id,
    ((c1.nb)::numeric - COALESCE(sum(c2.nb), (0)::numeric)) AS nb,
    c1.last,
    ((c1.nb)::numeric + COALESCE(sum(c2.nb), (0)::numeric)) AS total
   FROM (building_contribs c1
     LEFT JOIN building_contribs c2 ON (((c2.id = c1.id) AND (c2.rank > 1))))
  WHERE ((c1.rank = 1) AND (c1.nb >= 3))
  GROUP BY c1.id, c1.orientation, c1.nb, c1.rank, c1.first, c1.last
 HAVING (((c1.nb)::numeric - COALESCE(sum(c2.nb), (0)::numeric)) < (3)::numeric);


--
-- Name: buildings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE buildings (
    osm_id bigint,
    geom geometry,
    surface double precision,
    orientation numeric,
    orient_type integer
);


--
-- Name: building_geom_no_orient; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX building_geom_no_orient ON buildings USING gist (geom) WHERE (orient_type IS NULL);


--
-- Name: building_id_no_orient; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX building_id_no_orient ON buildings USING btree (osm_id) WHERE (orient_type IS NULL);


--
-- Name: building_orient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX building_orient_id ON building_orient USING btree (id);


--
-- Name: building_orient_idip; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX building_orient_idip ON building_orient USING btree (id, ip);


--
-- Name: building_orient_ip; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX building_orient_ip ON building_orient USING btree (ip);


--
-- Name: buildings_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX buildings_id ON buildings USING btree (osm_id);


--
-- Name: buildings_ok_geom; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX buildings_ok_geom ON buildings USING gist (geom);


--
-- PostgreSQL database dump complete
--

