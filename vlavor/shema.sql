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
  created TIMESTAMP NOT NULL DEFAULT CURRENT_DATE,
  type TEXT NOT NULL,
  description TEXT NOT NULL,
  region TEXT NOT NULL,
  area TEXT NOT NULL,
  address TEXT NOT NULL,
  takenby INTEGER,
  contact_name TEXT,
  contact_phone TEXT,
  done BOOLEAN NOT NULL
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
  username TEXT NOT NULL,
  check_bit INTEGER NOT NULL,
  refreshed INTEGER NOT NULL,
  logged_in INTEGER NOT NULL,
  PRIMARY KEY (username)
);

create table board(
id serial primary key,
title text,
description text,
doneby int,
posting_date DATE NOT NULL DEFAULT CURRENT_DATE
);
