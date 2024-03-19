-------------------------------------------------------------------------------
-- next_id --
-------------------------------------------------------------------------------
CREATE TABLE next_id (
  target VARCHAR(320) NOT NULL,
  next INT DEFAULT(0) NOT NULL CHECK (next >= 0),
  PRIMARY KEY(target));


-------------------------------------------------------------------------------
-- users --
-------------------------------------------------------------------------------
CREATE TABLE users (
  id INT PRIMARY KEY CHECK (id > 0),
  generation_ts CHAR(22) NOT NULL,
  init_ts CHAR(22) NOT NULL,
  email VARCHAR(320) NOT NULL UNIQUE CHECK (length(email) > 0),
  name VARCHAR(320) CHECK (name IS NULL OR length(name) > 0),
  -- "htdigest:<sha256>"
  password CHAR(73) NOT NULL UNIQUE CHECK (length(password) == 73),
  realm VARCHAR(253) NOT NULL CHECK (length(realm) > 0),
  excluded BOOL DEFAULT(FALSE) NOT NULL);

INSERT INTO next_id (target) VALUES ("users");

-------------------------------------------------------------------------------
-- uvns --
-------------------------------------------------------------------------------
CREATE TABLE uvns (
  id INT PRIMARY KEY CHECK (id > 0),
  generation_ts CHAR(22) NOT NULL,
  init_ts CHAR(22) NOT NULL,
  name VARCHAR(253) NOT NULL UNIQUE CHECK (length(name) > 0),
  address VARCHAR(253) UNIQUE CHECK (address IS NULL OR length(address) > 0),
  settings TEXT NOT NULL);

INSERT INTO next_id (target) VALUES ("uvns");


-------------------------------------------------------------------------------
-- uvns_credentials --
-------------------------------------------------------------------------------
CREATE TABLE uvns_credentials (
  owner INT NOT NULL,
  target INT NOT NULL,
  owned BOOL DEFAULT(FALSE) NOT NULL,
  PRIMARY KEY(owner, target),
  FOREIGN KEY(owner) REFERENCES user(id),
  FOREIGN KEY(target) REFERENCES uvns(id));


-------------------------------------------------------------------------------
-- registry --
-------------------------------------------------------------------------------
CREATE TABLE registry (
  id INT PRIMARY KEY CHECK (id > 0),
  generation_ts CHAR(22) NOT NULL,
  init_ts CHAR(22) NOT NULL,
  uvn_id INT NOT NULL CHECK (id > 0),
  rekeyed_root BOOL DEFAULT(FALSE) NOT NULL,
  deployment TEXT);

INSERT INTO next_id (target) VALUES ("registry");


-------------------------------------------------------------------------------
-- cells --
-------------------------------------------------------------------------------
CREATE TABLE cells (
  id INT PRIMARY KEY CHECK (id > 0),
  generation_ts CHAR(22) NOT NULL,
  init_ts CHAR(22) NOT NULL,
  name VARCHAR(253) NOT NULL UNIQUE CHECK (length(name) > 0),
  address VARCHAR(253) UNIQUE CHECK (address IS NULL OR length(address) > 0),
  settings TEXT NOT NULL,
  allowed_lans TEXT NOT NULL,
  uvn_id INT NOT NULL CHECK (id > 0),
  excluded BOOL DEFAULT(FALSE) NOT NULL,
  FOREIGN KEY (uvn_id) REFERENCES uvns(id));

INSERT INTO next_id (target) VALUES ("cells");


-------------------------------------------------------------------------------
-- cells_credentials --
-------------------------------------------------------------------------------
CREATE TABLE cells_credentials (
  owner INT NOT NULL,
  target INT NOT NULL,
  owned BOOL DEFAULT(FALSE) NOT NULL,
  PRIMARY KEY(owner, target),
  FOREIGN KEY(owner) REFERENCES user(id),
  FOREIGN KEY(target) REFERENCES cells(id));


-------------------------------------------------------------------------------
-- particles --
-------------------------------------------------------------------------------
CREATE TABLE particles (
  id INT PRIMARY KEY CHECK (id > 0),
  generation_ts CHAR(22) NOT NULL,
  init_ts CHAR(22) NOT NULL,
  name VARCHAR(253) NOT NULL UNIQUE CHECK (length(name) > 0),
  uvn_id INT NOT NULL CHECK (id > 0),
  excluded BOOL DEFAULT(FALSE) NOT NULL);

INSERT INTO next_id (target) VALUES ("particles");


-------------------------------------------------------------------------------
-- particles_credentials --
-------------------------------------------------------------------------------
CREATE TABLE particles_credentials (
  owner INT NOT NULL,
  target INT NOT NULL,
  owned BOOL DEFAULT(FALSE) NOT NULL,
  PRIMARY KEY(owner, target),
  FOREIGN KEY(owner) REFERENCES user(id),
  FOREIGN KEY(target) REFERENCES particles(id));


-------------------------------------------------------------------------------
-- asymm_keys --
-------------------------------------------------------------------------------
CREATE TABLE asymm_keys (
  id TEXT CHECK (length(id) > 0),
  generation_ts CHAR(22) NOT NULL,
  init_ts CHAR(22) NOT NULL,
  public TEXT NOT NULL UNIQUE,
  private TEXT NOT NULL UNIQUE,
  dropped BOOL DEFAULT(FALSE) NOT NULL,
  PRIMARY KEY(id, dropped) ON CONFLICT REPLACE);

------------------------------------------------------------------------------
-- symm_keys --
-------------------------------------------------------------------------------
CREATE TABLE symm_keys (
  id TEXT CHECK (length(id) > 0),
  generation_ts CHAR(22) NOT NULL,
  init_ts CHAR(22) NOT NULL,
  value TEXT NOT NULL UNIQUE,
  dropped BOOL DEFAULT(FALSE) NOT NULL,
  PRIMARY KEY(id, dropped) ON CONFLICT REPLACE);
