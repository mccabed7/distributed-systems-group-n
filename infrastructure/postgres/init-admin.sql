CREATE TABLE IF NOT EXISTS user_registrations (
    user_id UUID NOT NULL,
    registration_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, registration_id)
);

CREATE INDEX IF NOT EXISTS idx_registration_id ON user_registrations (registration_id);
