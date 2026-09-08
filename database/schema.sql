CREATE DATABASE IF NOT EXISTS campustrace;
USE campustrace;


SET FOREIGN_KEY_CHECKS = 0;


CREATE TABLE divisions (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,          -- e.g. 'Second Year CS-C'
    branch          VARCHAR(100) NOT NULL,           -- e.g. 'Computer Engineering'
    year            TINYINT UNSIGNED NOT NULL,        -- e.g. 2
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_division_name (name)
) ENGINE=InnoDB;

CREATE TABLE rooms (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(50) NOT NULL,             -- e.g. 'Lab 204'
    building        VARCHAR(100),
    capacity        SMALLINT UNSIGNED,
    UNIQUE KEY uq_room_name_building (name, building)
) ENGINE=InnoDB;

CREATE TABLE courses (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    division_id     INT UNSIGNED NOT NULL,
    code            VARCHAR(20) NOT NULL,             -- e.g. 'CS201'
    name            VARCHAR(150) NOT NULL,
    course_type     ENUM('theory','lab','tutorial') NOT NULL,
    FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE,
    INDEX idx_course_division (division_id)
) ENGINE=InnoDB;

CREATE TABLE batches (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    course_id       INT UNSIGNED NOT NULL,
    name            VARCHAR(20) NOT NULL,             -- e.g. 'B1'
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE KEY uq_batch_course_name (course_id, name)
) ENGINE=InnoDB;

CREATE TABLE users (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(150) NOT NULL,
    email           VARCHAR(150) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            ENUM('student','course_faculty','class_teacher',
                          'health_admin','institute_admin') NOT NULL,

    division_id     INT UNSIGNED NULL,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE SET NULL,
    UNIQUE KEY uq_user_email (email),
    INDEX idx_user_role (role),
    INDEX idx_user_division (division_id)
) ENGINE=InnoDB;

CREATE TABLE faculty_course_assignments (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    faculty_id      INT UNSIGNED NOT NULL,
    course_id       INT UNSIGNED NOT NULL,
    FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE KEY uq_faculty_course (faculty_id, course_id),
    INDEX idx_fca_course (course_id)
) ENGINE=InnoDB;

CREATE TABLE enrollments (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id      INT UNSIGNED NOT NULL,
    course_id       INT UNSIGNED NOT NULL,
    batch_id        INT UNSIGNED NULL,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE SET NULL,
    UNIQUE KEY uq_enrollment (student_id, course_id),
    INDEX idx_enrollment_course_batch (course_id, batch_id)
) ENGINE=InnoDB;

CREATE TABLE timetable_slots (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    course_id       INT UNSIGNED NOT NULL,
    room_id         INT UNSIGNED NOT NULL,
    batch_id        INT UNSIGNED NULL,        -- NULL = whole-division/theory slot
    day_of_week     TINYINT UNSIGNED NOT NULL, -- 0=Mon .. 6=Sun
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE RESTRICT,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
    -- This index is what the nightly presence builder scans by room+day.
    INDEX idx_slot_room_day (room_id, day_of_week),
    INDEX idx_slot_course (course_id)
) ENGINE=InnoDB;

CREATE TABLE presence (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    room_id         INT UNSIGNED NOT NULL,
    slot_id         INT UNSIGNED NOT NULL,
    presence_date   DATE NOT NULL,
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (slot_id) REFERENCES timetable_slots(id) ON DELETE CASCADE,
    UNIQUE KEY uq_presence (user_id, slot_id, presence_date),
    
    INDEX idx_presence_room_slot_date (room_id, slot_id, presence_date),
    INDEX idx_presence_user_date (user_id, presence_date)
) ENGINE=InnoDB;

CREATE TABLE contact_edges (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_a_id           INT UNSIGNED NOT NULL,
    user_b_id           INT UNSIGNED NOT NULL,
    room_id             INT UNSIGNED NOT NULL,
    contact_date        DATE NOT NULL,
    duration_minutes    SMALLINT UNSIGNED NOT NULL,
    room_type_weight    DECIMAL(4,3) NOT NULL DEFAULT 1.000, -- e.g. lab > lecture hall
    FOREIGN KEY (user_a_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user_b_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
    UNIQUE KEY uq_edge (user_a_id, user_b_id, contact_date, room_id),
  
    INDEX idx_edge_a_date (user_a_id, contact_date),
    INDEX idx_edge_b_date (user_b_id, contact_date)
) ENGINE=InnoDB;


CREATE TABLE disease_kb (
    id                      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name                    VARCHAR(100) NOT NULL,
    symptoms                TEXT NOT NULL,
    preventive_measures     TEXT NOT NULL,
    incubation_period_days  SMALLINT UNSIGNED,
    added_by                INT UNSIGNED NULL,       -- health_admin user
    approved_by             INT UNSIGNED NULL,       -- institute_admin user, if sign-off used
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY uq_disease_name (name)
) ENGINE=InnoDB;

CREATE TABLE health_records (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             INT UNSIGNED NOT NULL,
    disease_id          INT UNSIGNED NULL,           -- NULL until matched/confirmed
    custom_symptoms     TEXT NULL,
    onset_date          DATE NOT NULL,
    severity            ENUM('mild','moderate','severe') NOT NULL,
    status              ENUM('reported','confirmed','recovered') NOT NULL DEFAULT 'reported',
    reported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_by        INT UNSIGNED NULL,           -- health_admin user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_id) REFERENCES disease_kb(id) ON DELETE SET NULL,
    FOREIGN KEY (confirmed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_health_user (user_id),
    INDEX idx_health_status_date (status, onset_date)
) ENGINE=InnoDB;

CREATE TABLE absence_flags (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id          INT UNSIGNED NOT NULL,
    course_id           INT UNSIGNED NOT NULL,
    faculty_id          INT UNSIGNED NOT NULL,
    flagged_date        DATE NOT NULL,
    reason_category     VARCHAR(100) NOT NULL,       -- category, not a diagnosis
    state               ENUM('pending','confirmed','dismissed') NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_absence_student (student_id),
    INDEX idx_absence_state (state)
) ENGINE=InnoDB;


CREATE TABLE alerts (
    id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id                 INT UNSIGNED NOT NULL,        -- recipient
    source_health_record_id INT UNSIGNED NOT NULL,        -- the reported case that triggered tracing
    risk_level              ENUM('low','medium','high') NOT NULL,
    risk_score              DECIMAL(5,2) NOT NULL,
    symptoms_snapshot       TEXT NOT NULL,                 -- denormalized so it survives KB edits
    precautions_snapshot    TEXT NOT NULL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at         TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (source_health_record_id) REFERENCES health_records(id) ON DELETE CASCADE,
    INDEX idx_alert_user (user_id),
    INDEX idx_alert_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE feedback (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    alert_id            BIGINT UNSIGNED NOT NULL,
    is_false_positive   BOOLEAN NOT NULL,
    submitted_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by         INT UNSIGNED NULL,           -- health_admin who reviewed it
    weight_adjusted     BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY uq_feedback_alert (alert_id)
) ENGINE=InnoDB;


CREATE TABLE capacity (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    facility_name   VARCHAR(100) NOT NULL,
    total_beds      SMALLINT UNSIGNED NOT NULL,
    occupied_beds   SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE isolation_allocations (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    capacity_id     INT UNSIGNED NOT NULL,
    priority_score  DECIMAL(5,2) NOT NULL,           -- from the priority queue at allocation time
    allocated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    released_at     TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (capacity_id) REFERENCES capacity(id) ON DELETE CASCADE,
    INDEX idx_isolation_active (capacity_id, released_at)
) ENGINE=InnoDB;


CREATE TABLE system_config (
    id                      TINYINT UNSIGNED PRIMARY KEY DEFAULT 1,
    k_anonymity_threshold   SMALLINT UNSIGNED NOT NULL DEFAULT 5,
    default_tracing_depth   TINYINT UNSIGNED NOT NULL DEFAULT 2,
    default_tracing_direction ENUM('forward','backward','both') NOT NULL DEFAULT 'both',
    updated_by              INT UNSIGNED NULL,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT chk_single_row CHECK (id = 1)
) ENGINE=InnoDB;

CREATE TABLE audit_log (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,           -- who performed the action
    action          VARCHAR(100) NOT NULL,           -- e.g. 'view_contact_graph', 'edit_disease_kb'
    target_type     VARCHAR(50) NULL,                -- e.g. 'health_record', 'contact_edge'
    target_id       BIGINT UNSIGNED NULL,
    details         JSON NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

    INDEX idx_audit_user_date (user_id, created_at),
    INDEX idx_audit_action_date (action, created_at)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;