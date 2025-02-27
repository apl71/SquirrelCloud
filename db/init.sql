CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS AppUser (
    uuid        varchar(256)    PRIMARY KEY DEFAULT uuid_generate_v4(),
    username    varchar(256)    NOT NULL,
    email       varchar(256)    NOT NULL,
    pswhash     varchar(256)    NOT NULL,
    role        varchar(256)    NOT NULL,
    create_at   timestamp       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT  APPUSER_USERNAME    UNIQUE (username),
    CONSTRAINT  APPUSER_EMAIL       UNIQUE (email)
);
-- ROLE_ADMIN, ROLE_USER

INSERT INTO AppUser (username, email, pswhash, role) VALUES ('admin', 'admin@example.com', crypt('admin', gen_salt('md5')), 'ROLE_ADMIN') ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS Session (
    user_uuid   varchar(256)    NOT NULL,
    session     varchar(256)    PRIMARY KEY NOT NULL,
    create_at   timestamp       DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS File (
    uuid        varchar(256)    PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_uuid  varchar(256)    NOT NULL,
    share_uuid  varchar(256)[]  DEFAULT array[]::varchar[],
    type        varchar(16)     NOT NULL,
    hash        varchar(128),
    size        varchar(64),
    tag_uuid    varchar(256)[]  DEFAULT array[]::varchar[],
    remark      varchar(256),
    create_at   timestamp       DEFAULT CURRENT_TIMESTAMP,
    path        varchar(1024),
    pinned      boolean         DEFAULT false,
    CONSTRAINT  FILE_UNIQUE_PATH    UNIQUE (owner_uuid, path)
);
-- TYPE_DIR, TYPE_FILE, TYPE_LINK
INSERT INTO File (owner_uuid, type, path) VALUES ((SELECT uuid FROM AppUser WHERE username = 'admin'), 'TYPE_DIR', '/') ON CONFLICT DO NOTHING;
ALTER TABLE File
ALTER COLUMN size TYPE bigint USING size::bigint;

CREATE TABLE IF NOT EXISTS Link (
    uuid        varchar(256)    PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_uuid  varchar(256)    NOT NULL,
    path        varchar(1024)   NOT NULL,
    target_uuid varchar(256)    NOT NULL,
    target_path varchar(1024)   NOT NULL,
    CONSTRAINT  UNIQUE_LINK      UNIQUE (path, owner_uuid)
);

CREATE TABLE IF NOT EXISTS Tag (
    uuid        varchar(256)    PRIMARY KEY DEFAULT uuid_generate_v4(),
    text        varchar(256)    NOT NULL,
    owner_uuid  varchar(256)    NOT NULL,
    CONSTRAINT  UNIQUE_TAG      UNIQUE (text, owner_uuid)
);

CREATE TABLE IF NOT EXISTS ExternalLink (
    uuid        varchar(256)    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_uuid   varchar(256)    NOT NULL,
    file_path   varchar(1024)   NOT NULL,
    share_key   varchar(64)     DEFAULT uuid_generate_v4(),
    expire      timestamp       NOT NULL
);

CREATE TABLE IF NOT EXISTS Notification (
    uuid                varchar(256)    PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_user_uuid      varchar(256)    NOT NULL,
    to_user_uuid        varchar(256)    NOT NULL,
    title               varchar(256)    NOT NULL,
    content             text            NOT NULL,
    type                varchar(64)     NOT NULL,
    meta                varchar(1024),
    create_at           timestamp       DEFAULT CURRENT_TIMESTAMP
);
-- TYPE_INFO, TYPE_SHARE_REQUEST
-- meta for metadata, e.g. path of share request directory