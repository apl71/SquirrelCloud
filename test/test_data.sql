INSERT INTO AppUser (username, email, pswhash, role) VALUES
    ('alice', 'alice@example.com', crypt('alice123', gen_salt('md5')), 'ROLE_USER'),
    ('bob', 'bob@example.com', crypt('bob123', gen_salt('md5')), 'ROLE_USER')
ON CONFLICT DO NOTHING;


INSERT INTO File (owner_uuid, type, path) VALUES
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/'),
    ((SELECT uuid FROM AppUser WHERE username = 'bob'), 'TYPE_DIR', '/')
ON CONFLICT DO NOTHING;


-- Realistic directory tree for alice
INSERT INTO File (owner_uuid, type, path) VALUES
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/Documents'),
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/Documents/Work'),
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/Documents/Notes'),
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/Pictures'),
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/Pictures/Trips'),
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/Downloads'),
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/Music'),
    ((SELECT uuid FROM AppUser WHERE username = 'alice'), 'TYPE_DIR', '/recycle')
ON CONFLICT DO NOTHING;

INSERT INTO File (owner_uuid, type, path, hash, size, remark, pinned) VALUES
    (
        (SELECT uuid FROM AppUser WHERE username = 'alice'),
        'TYPE_FILE',
        '/Documents/Work/project-plan.md',
        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        4096,
        'Main planning document.',
        true
    ),
    (
        (SELECT uuid FROM AppUser WHERE username = 'alice'),
        'TYPE_FILE',
        '/Documents/Notes/todo.txt',
        'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
        512,
        'Small personal todo list.',
        false
    ),
    (
        (SELECT uuid FROM AppUser WHERE username = 'alice'),
        'TYPE_FILE',
        '/Pictures/Trips/beach.jpg',
        'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
        245760,
        'Trip photo.',
        false
    ),
    (
        (SELECT uuid FROM AppUser WHERE username = 'alice'),
        'TYPE_FILE',
        '/Downloads/archive.zip',
        'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
        1048576,
        'Downloaded test archive.',
        false
    ),
    (
        (SELECT uuid FROM AppUser WHERE username = 'alice'),
        'TYPE_FILE',
        '/Music/theme.mp3',
        'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
        5242880,
        'Theme music sample.',
        false
    )
ON CONFLICT DO NOTHING;

-- Realistic directory tree for bob
INSERT INTO File (owner_uuid, type, path) VALUES
    ((SELECT uuid FROM AppUser WHERE username = 'bob'), 'TYPE_DIR', '/Projects'),
    ((SELECT uuid FROM AppUser WHERE username = 'bob'), 'TYPE_DIR', '/Projects/demo-app'),
    ((SELECT uuid FROM AppUser WHERE username = 'bob'), 'TYPE_DIR', '/Projects/demo-app/src'),
    ((SELECT uuid FROM AppUser WHERE username = 'bob'), 'TYPE_DIR', '/Pictures'),
    ((SELECT uuid FROM AppUser WHERE username = 'bob'), 'TYPE_DIR', '/Shared'),
    ((SELECT uuid FROM AppUser WHERE username = 'bob'), 'TYPE_DIR', '/recycle')
ON CONFLICT DO NOTHING;

INSERT INTO File (owner_uuid, type, path, hash, size, remark, pinned) VALUES
    (
        (SELECT uuid FROM AppUser WHERE username = 'bob'),
        'TYPE_FILE',
        '/Projects/demo-app/README.md',
        'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
        2048,
        'Demo application readme.',
        true
    ),
    (
        (SELECT uuid FROM AppUser WHERE username = 'bob'),
        'TYPE_FILE',
        '/Projects/demo-app/src/main.py',
        '1111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111',
        8192,
        'Entry point for demo app.',
        false
    ),
    (
        (SELECT uuid FROM AppUser WHERE username = 'bob'),
        'TYPE_FILE',
        '/Pictures/avatar.png',
        '2222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222',
        65536,
        'Profile avatar.',
        false
    ),
    (
        (SELECT uuid FROM AppUser WHERE username = 'bob'),
        'TYPE_FILE',
        '/Shared/meeting-notes.pdf',
        '3333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333',
        98304,
        'Shared meeting notes.',
        false
    )
ON CONFLICT DO NOTHING;