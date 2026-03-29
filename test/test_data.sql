

INSERT INTO AppUser (username, email, pswhash, role) VALUES
    ('alice', 'alice@example.com', crypt('alice123', gen_salt('md5')), 'ROLE_USER'),
    ('bob', 'bob@example.com', crypt('bob123', gen_salt('md5')), 'ROLE_USER')
ON CONFLICT DO NOTHING;

INSERT INTO File (owner_uuid, type, path) VALUES
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/'),
    ((SELECT uuid FROM AppUser WHERE username = 'bob'), 'TYPE_DIR', '/')
ON CONFLICT DO NOTHING;