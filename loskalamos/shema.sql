DROP TABLE IF EXISTS technician;
DROP TABLE IF EXISTS report;
DROP TABLE IF EXISTS region;
DROP TABLE IF EXISTS area;
DROP TABLE IF EXISTS update_check;

CREATE TABLE technician (
  id SERIAL,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  type TEXT NOT NULL,
  region TEXT NOT NULL
);

CREATE TABLE report (
  id SERIAL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  type TEXT NOT NULL,
  description TEXT NOT NULL,
  region TEXT NOT NULL,
  area TEXT NOT NULL,
  address TEXT NOT NULL,
  takenby INTEGER,
  contact_name TEXT,
  contact_phone TEXT
);

CREATE TABLE region (
  id SERIAL,
  name TEXT NOT NULL PRIMARY KEY

);

CREATE TABLE area (
  id SERIAL,
  name TEXT NOT NULL,
  region_id INTEGER NOT NULL,
  PRIMARY KEY (name, region_id)
);

CREATE TABLE update_check(
  id SERIAL,
  check_bit INTEGER NOT NULL
);
INSERT INTO update_check check_bit VALUES (0);
