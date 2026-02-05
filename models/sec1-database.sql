DROP TABLE IF EXISTS SALON_USER CASCADE;
DROP TABLE IF EXISTS SALON_APPOINTMENT CASCADE;
DROP TABLE IF EXISTS SALON_REPORT CASCADE;
DROP TABLE IF EXISTS SALON_SERVICE CASCADE;
DROP TABLE IF EXISTS SALON_LOG CASCADE;

CREATE TABLE SALON_USER (
    user_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    active SMALLINT DEFAULT 1,
    user_type VARCHAR(15) DEFAULT 'client',  -- client / professional / admin_user / admin_appoint / super
    access_level SMALLINT DEFAULT 1,
    user_name VARCHAR(25) NOT NULL UNIQUE,
    fname VARCHAR(15) NOT NULL,
    lname VARCHAR(15) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    user_image VARCHAR(100) DEFAULT 'default.jpeg',
    password TEXT NOT NULL,
    phone_number VARCHAR(15) DEFAULT '514-123-4567',
    address VARCHAR(15) DEFAULT 'Montreal',
    age INTEGER DEFAULT 18,
    pay_rate NUMERIC(5,2) DEFAULT 15.75,
    specialty VARCHAR(15) DEFAULT 'Hair-dresser',
    warning TEXT,
    warning_count INTEGER DEFAULT 0,
    CONSTRAINT unique_user_email UNIQUE (user_name, email)
);
 
-- $2b$12$gqsQ8F1vZRxuRj.k2PM57eL/NA.Y/b6FxJ0SfihztJdlcPw7q2E9G'
-- >>> gen_pw('12')
-- '$2b$12$X6WVyVmfu98fH7KxjDYSCuPCqAnJa/o.RHaPxZi6Ojgq0u4ZXo6Vm'
-- >>> gen_pw('13')
-- '$2b$12$q69QDA9zTxE3z1alMe4Nzuk2i6h4RP6TFkhriRm1vjwurnMApdg9i'

--------------  admins -----------------
-- Admins
INSERT INTO SALON_USER (user_type, access_level, user_name, fname, lname, email, password, phone_number, address, age,
                        user_image, pay_rate, specialty, warning, warning_count)
VALUES 
('admin_user', 2, 'badr', 'badrr', 'badrlast', 'badr@email.com', 
 'scrypt:32768:8:1$hUEzyeDTw138lpLb$3165c3f60f8787271d7e8db3daf102ac16eb72a53e2127cf1c34da5c7ff0c51f23cf8f0a0f7d246d3ff7e77c3c22e3af8182e2d4f9c7b0ad6d3db59afd29a1d0', 
 '514-1234567', 'addr2', 18, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0),

 ('admin_super', 3, 'nasr', 'nasr', 'teacher', 'nasr@gmail.com', 
 'scrypt:32768:8:1$fGSCiio8jb755QhT$58778b0b0fa1f45b370f02a8290b49eb07d566f977095fa919a791715ab752ad0daa7e75d0f4e15ac8b5784f3acc48d7168af057200287490354f084ec2898c7', 
 '514-1234567', 'addr2', 18, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0),

 ('admin_user', 2, 'user_manager1', 'user', 'manager', 'user_manager1@gmail.com', 
 'scrypt:32768:8:1$fGSCiio8jb755QhT$58778b0b0fa1f45b370f02a8290b49eb07d566f977095fa919a791715ab752ad0daa7e75d0f4e15ac8b5784f3acc48d7168af057200287490354f084ec2898c7', 
 '514-1234567', 'addr2', 18, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0),

 ('admin_appoint', 2, 'appoint_manager1', 'appoint', 'manager', 'appoint_manager1@gmail.com', 
 'scrypt:32768:8:1$5vCGuohq5Y42ugK3$fce7c05138989aa147e056d942815acbed607c7e65a452062023595a376f7f38bb4dd548d7bfda2d70aaae18256290357c5bd2dddbface660e00bbf6177bfcfc', 
 '514-1234567', 'addr2', 18, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0),

 ('admin_super', 3, 'andrew', 'Andrew', 'Marks', 'andrew@email.com', 
 'scrypt:32768:8:1$KonIWXkddMOqSHRJ$6c7f610d4c25d30a3942b0d564e95918a9f9b82ec392f058c7eb4d091633736c013a83642e9506d8d99745efdbda3823c0b75fa663b938eee0712d9f3f0d026a', 
 '514-1234567', 'addr2', 18, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0),

 ('admin_super', 3, 'alexander', 'Alexander', 'Roxas', 'alexander@email.com', 
 'scrypt:32768:8:1$KonIWXkddMOqSHRJ$6c7f610d4c25d30a3942b0d564e95918a9f9b82ec392f058c7eb4d091633736c013a83642e9506d8d99745efdbda3823c0b75fa663b938eee0712d9f3f0d026a', 
 '514-1234567', 'addr2', 18, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0),

 ('admin_super', 3, 'rix', 'Rix', 'Njoumene', 'rix@email.com', 
 'scrypt:32768:8:1$KonIWXkddMOqSHRJ$6c7f610d4c25d30a3942b0d564e95918a9f9b82ec392f058c7eb4d091633736c013a83642e9506d8d99745efdbda3823c0b75fa663b938eee0712d9f3f0d026a', 
 '514-1234567', 'addr2', 18, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0);

-- Clients
INSERT INTO SALON_USER (
    user_type, access_level, user_name, fname, lname, email,
    password, phone_number, address, age, user_image, pay_rate,
    specialty, warning, warning_count, active
)
VALUES 
('client', 1, 'client1', 'Sophia', 'Johnson', 'client1@email.com',
 'scrypt:32768:8:1$VcaZ3MQiv7hTj5vv$4788f618ccf71d28d2de6217eb27901ff92c3b38ae56b5598a8da32b1ea485a93050a317a5456de4d51b8f0614d901df07439a038ecfddc3008da5ac8ce2c14e',
 '514-1234567', 'laval', 22, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0, 1),

('client', 1, 'client2', 'Liam', 'Carter', 'client2@email.com',
 'scrypt:32768:8:1$OfjUbysmSUzD926N$9049a7f6a1bd1570ec43dba8b0b811e844597e55f44e15283a4c571d0ee573065cfbe8d54cdd5cd0c76cd6e097a4f94aac03168c3fed0979ba9870494a8d6437',
 '514-1234567', 'laval', 23, 'default.jpeg', 15.75, 'Hair-dresser', 'Late for appointment', 1, 1),

('client', 1, 'client3', 'Isabella', 'Nguyen', 'client3@email.com',
 'scrypt:32768:8:1$CPLHb0LjHjQSlbao$9f5a81813f4e9d8b46cc248512c193ce61043c18823196483a42b9d7bd2855db0e12bea4081b655dfa6e2d67c81a645bb11429ca9244ec77b7be328bd842ebfd',
 '514-1234567', 'laval', 22, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0, 1),

('client', 1, 'client4', 'Noah', 'Patel', 'client4@email.com',
 'scrypt:32768:8:1$6JCXPxN0b6PwUjtJ$a2de813f9a01b4abf9f57bada31b091698b869573dc1a8fa55f692573f0b0f435e308d20d7f6581cf87c13ccabdd088fc038d4bde4304261d91a469880473756',
 '514-1234567', 'laval', 23, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0, 0),

('client', 1, 'client10eng', 'Maya', 'Thompson', 'client10eng@email.com',
 'scrypt:32768:8:1$BJJMffSlIKcsqGPe$f6826b85cbc7875771382ded27038532515ee60145bd5377bd5d43607140d3692e67a2df280507bdab71c019efa33d8834777068b5889d95a56b0ba779231830',
 '514-4567890', 'Montreal', 24, 'default.jpeg', 15.75, 'Hair-dresser', 'Rude behavior to staff', 1, 1),

('client', 1, 'client1phy', 'Elijah', 'Morales', 'client1phy@email.com',
 'scrypt:32768:8:1$gWEOmokhE2pRBjYV$14123be1ef0e1a18b6b2357a982d03a5e96a9a3a9ef95f471d6f917b24cfcbcbed9a2df8d2e4eebd18163ebbb10783d7673479e3a6e2f857799c389408a2cbfa',
 'phy', 'Sce', 2022, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0, 1);


-- Professionals
INSERT INTO SALON_USER (
    user_type, access_level, user_name, fname, lname, email,
    password, phone_number, address, age, user_image, pay_rate,
    specialty, warning, warning_count, active
)
VALUES 
('professional', 1, 'employee1', 'Ava', 'Robinson', 'employee1@email.com',
 'scrypt:32768:8:1$os0dHggcpAkoM4LV$3d5ae894273f658bb483ba60ec981f5569453869b5cefd61546964881bf99d79dc3ff45f3346855968c843dbae4359e5da6d6943059f6a1d9d5124830992dd92',
 '514-1234567', 'laval', 22, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0, 1),

('professional', 1, 'employee2', 'Ethan', 'Dubois', 'employee2@email.com',
 'scrypt:32768:8:1$omBzzI8TPjnl1O0G$04372843c49f6afaf9b314d52ed66fd0d6a469a592641c8f57116ba9c4bc0fd535729df6b1ca998ab719da853021264b7e66414548cb16903e11e0ef63964c70',
 '514-1234567', 'laval', 22, 'default.jpeg', 20.00, 'Hair-dresser', 'Unprofessional behavior', 1, 1),

('professional', 1, 'employee3', 'Chloe', 'Park', 'employee3@email.com',
 'scrypt:32768:8:1$AblXoWxEy246wRdX$0e7c3a48f682c69a1cfdf67380457230aacd418af379becfa22976c85b9a283eb2024aab515062ddc5516bfd1079242f3fc2423cc29f0c81d841295285485337',
 '514-1234567', 'laval', 22, 'default.jpeg', 30.00, 'Hair-dresser', NULL, 0, 1),

('professional', 1, 'employee4', 'Lucas', 'Moretti', 'employee4@email.com',
 'scrypt:32768:8:1$vDKHmwSD5JfLu9Ry$4c75cad1aab211880237957a88a8dfd3df6e0c6cd5008590d90d448a740ec4490ebcb197a773c714c2b9be118d8b3ffa65283bcf5216306ab691e21b804e973a',
 '514-4567890', 'Montreal', 24, 'default.jpeg', 25.00, 'Hair-dresser', NULL, 0, 0),

('professional', 1, 'employee5', 'Zoe', 'Martin', 'employee5@email.com',
 'scrypt:32768:8:1$sMCuiLXR9HcPPB0f$a4336071cb5b6c233205c9feb3071d46846d32ae38cd417ebd19548dceb67b831c8f3c5b98757f6ee50e16d46f2766301aba7a67bac59d4b43e8df42f04dc915',
 '514-4567890', 'Montreal', 24, 'default.jpeg', 15.75, 'Hair-dresser', NULL, 0, 1),

('professional', 1, 'employee6', 'Jackson', 'Livingston', 'employee6@email.com',
 'scrypt:32768:8:1$JwM3HWxSOa4BnqcJ$23009e3a4e4b397a63e4f4b5157685e6247493a1b6919faf45f8f2f323733993e6c261dbe0fc6e4542be83209613b95f1f8d8950b569e36f3484374530234237',
 '438-12345678', 'ottawa', 28, 'default.jpeg', 20.00, 'Hair-dresser', 'Client complaint received', 1, 1),

('professional', 1, 'employee7', 'Emma', 'Lefebvre', 'employee7@email.com',
 'scrypt:32768:8:1$4i8lA5PPpkorqzTr$616e7d99a1ad0190756550621de12b2cb76f6eeb2e01b44574b4a1d1d19722bc7022c9364d9a7fa9b4e07c49c0ee494da5b6958bafe5b57af9254fcbf29eecfe',
 '438-12345678', 'ottawa', 28, 'default.jpeg', 17.50, 'Hair-dresser', NULL, 0, 1);


 
-- -------------------------------------------------

CREATE TABLE SALON_APPOINTMENT (
    appointment_id SERIAL PRIMARY KEY,
    status VARCHAR(10) DEFAULT 'requested',
    approved SMALLINT DEFAULT 0,
    date_appoint DATE DEFAULT CURRENT_DATE,
    slot VARCHAR(10) DEFAULT '9-10',
    venue VARCHAR(20) DEFAULT 'cmn_room',

    consumer_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,

    consumer_name VARCHAR(50) NOT NULL,
    provider_name VARCHAR(50) NOT NULL,
    nber_services SMALLINT DEFAULT 1,

    consumer_report VARCHAR(500),
    provider_report VARCHAR(500),

    CONSTRAINT salon_consumer_fk FOREIGN KEY (consumer_id) REFERENCES SALON_USER(user_id),
    CONSTRAINT salon_provider_fk FOREIGN KEY (provider_id) REFERENCES SALON_USER(user_id)
);


   
-- Client1 appointments
INSERT INTO SALON_APPOINTMENT (status, slot, venue, date_appoint, consumer_id, provider_id, consumer_name, provider_name)
VALUES 
('accepted', '10-11', 'room1', '2025-05-01',
 (SELECT user_id FROM salon_user WHERE user_name = 'client1'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee1'),
 'client1', 'employee1');

INSERT INTO SALON_APPOINTMENT (status, slot, venue, date_appoint, consumer_id, provider_id, consumer_name, provider_name)
VALUES 
('accepted', '9-10', 'room2', '2025-05-02',
 (SELECT user_id FROM salon_user WHERE user_name = 'client1'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee3'),
 'client1', 'employee3');

-- Client2
INSERT INTO SALON_APPOINTMENT (status, slot, venue, date_appoint, consumer_id, provider_id, consumer_name, provider_name)
VALUES 
('accepted', '3-4', 'chair1', '2025-05-03',
 (SELECT user_id FROM salon_user WHERE user_name = 'client2'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee2'),
 'client2', 'employee2');

-- Client3
INSERT INTO SALON_APPOINTMENT (status, slot, venue, date_appoint, consumer_id, provider_id, consumer_name, provider_name)
VALUES 
('accepted', '3-4', 'chair2', '2025-05-04',
 (SELECT user_id FROM salon_user WHERE user_name = 'client3'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee3'),
 'client3', 'employee3');

-- Accepted appointments
INSERT INTO SALON_APPOINTMENT (status, slot, venue, date_appoint, consumer_id, provider_id, consumer_name, provider_name)
VALUES 
('accepted', '11-12', 'room1', '2025-05-05',
 (SELECT user_id FROM salon_user WHERE user_name = 'client10eng'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee2'),
 'client10eng', 'employee2');

INSERT INTO SALON_APPOINTMENT (status, slot, venue, date_appoint, consumer_id, provider_id, consumer_name, provider_name)
VALUES 
('accepted', '14-15', 'room2', '2025-05-06',
 (SELECT user_id FROM salon_user WHERE user_name = 'client1phy'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee6'),
 'client1phy', 'employee6');

INSERT INTO SALON_APPOINTMENT (status, slot, venue, date_appoint, consumer_id, provider_id, consumer_name, provider_name)
VALUES 
('accepted', '13-14', 'chair1', '2025-05-07',
 (SELECT user_id FROM salon_user WHERE user_name = 'client2'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee3'),
 'client2', 'employee3');

-- Batch insert using dynamic IDs
INSERT INTO SALON_APPOINTMENT (status, slot, venue, date_appoint, consumer_id, provider_id, consumer_name, provider_name)
VALUES 
('requested', '14-15', 'chair1', '2025-05-13',
 (SELECT user_id FROM salon_user WHERE user_name = 'client1'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee3'),
 'client1', 'employee3'),

('accepted', '13-14', 'chair1', '2025-05-10',
 (SELECT user_id FROM salon_user WHERE user_name = 'client4'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee3'),
 'client4', 'employee3'),

('requested', '10-11', 'room1', '2025-05-15',
 (SELECT user_id FROM salon_user WHERE user_name = 'client4'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee5'),
 'client4', 'employee5'),

('accepted', '10-11', 'chair1', '2025-05-08',
 (SELECT user_id FROM salon_user WHERE user_name = 'client10eng'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee3'),
 'client10eng', 'employee3'),

('requested', '11-12', 'chair2', '2025-05-17',
 (SELECT user_id FROM salon_user WHERE user_name = 'client1phy'),
 (SELECT user_id FROM salon_user WHERE user_name = 'employee4'),
 'client1phy', 'employee4');




 
-- -------------------------------------------------
--------------------------
-- select * from SALON_APPOINTMENT order by salon_appointment_id;
CREATE TABLE SALON_REPORT (
    report_id SERIAL PRIMARY KEY,
    appointment_id INTEGER,
    status VARCHAR(10) DEFAULT 'inactive',  -- closed, done, grieve, complaint
    date_report DATE DEFAULT CURRENT_DATE,
    feedback_professional VARCHAR(500),
    feedback_client VARCHAR(500),
    client_seen BOOLEAN DEFAULT FALSE,
    flagged_by_professional BOOLEAN DEFAULT FALSE,

    CONSTRAINT salon_appointment_fk FOREIGN KEY (appointment_id) REFERENCES SALON_APPOINTMENT(appointment_id)
);

INSERT INTO SALON_REPORT (appointment_id, status, date_report, feedback_client, feedback_professional, client_seen, flagged_by_professional)
VALUES (1, 'closed', '2025-05-01', 'was a good hour', 'any time', TRUE, FALSE);

INSERT INTO SALON_REPORT (appointment_id, status, date_report, feedback_client, feedback_professional, client_seen, flagged_by_professional)
VALUES (2, 'closed', '2025-05-02', 'Discrimination', 'any thing from this entitled client!', TRUE, TRUE);

INSERT INTO SALON_REPORT (appointment_id, status, date_report, feedback_client, feedback_professional, client_seen, flagged_by_professional)
VALUES (3, 'closed', '2025-05-03', 'nice job', 'thansk!', TRUE, FALSE);

INSERT INTO SALON_REPORT (appointment_id, status, date_report, feedback_client, feedback_professional, client_seen, flagged_by_professional)
VALUES (4, 'closed', '2025-05-04', 'ok', 'ok??', TRUE, FALSE);

-- Open reports (no professional response yet)
INSERT INTO SALON_REPORT (appointment_id, status, date_report, feedback_client, feedback_professional, client_seen, flagged_by_professional)
VALUES 
(5, 'open', '2025-05-05', 'please review my issue', NULL, FALSE, FALSE),

(6, 'open', '2025-05-06', 'stylist didn’t listen', NULL, FALSE, TRUE);  -- flagged

-- Closed but flagged
INSERT INTO SALON_REPORT (appointment_id, status, date_report, feedback_client, feedback_professional, client_seen, flagged_by_professional)
VALUES 
(7, 'closed', '2025-05-07', 'resolved, but keep an eye', 'acknowledged', TRUE, TRUE);



COMMIT;
--------------SALON_SERVICE___________________
CREATE TABLE SALON_SERVICE
(service_id INTEGER GENERATED BY DEFAULT AS IDENTITY,
appointment_id  INTEGER ,
service_name  VARCHAR(35) default ('inactive'),
service_duration  SMALLINT default (1),   
service_price  Decimal(5,2) ,
service_materials  VARCHAR(35) default ('none'),  
CONSTRAINT  salon_service_pk PRIMARY KEY(service_id),
CONSTRAINT salon_servicet_fk FOREIGN KEY (appointment_id) REFERENCES SALON_APPOINTMENT (appointment_id)
); 

INSERT INTO salon_service (
    appointment_id, service_name, service_duration, service_price, service_materials
) VALUES
-- Requested appointments
(1, 'Hair Cut', 1, 15.75, 'Scissors'),
(2, 'Beard Trim', 2, 60.00, 'Razor'),
(3, 'Shampoo & Wash', 1, 20.00, 'Shampoo'),
(4, 'Hair Color Consultation', 2, 60.00, 'Color Chart'),

-- Accepted appointments
(5, 'Hair Cut', 1, 20.00, 'Scissors'),
(6, 'Beard Styling', 1, 20.00, 'Comb & Gel'),
(7, 'Hair Cut & Wash', 2, 60.00, 'Combo Kit');

-- Services (assume appointment_id 8–12 follow from auto-increment)
INSERT INTO SALON_SERVICE (appointment_id, service_name, service_duration, service_price, service_materials)
VALUES
(8,  'Wash & Blowdry', 1, 30.00, 'Color Kit'),
(9,  'Coloring',       1, 30.00, 'Color Kit'),
(10, 'Coloring',       2, 31.50, 'Razor'),
(11, 'Hair Cut',       1, 30.00, 'Razor'),
(12, 'Wash & Blowdry', 2, 50.00, 'Razor');



CREATE TABLE SALON_LOG (
    log_id SERIAL PRIMARY KEY,
    user_action TEXT,
    action_by TEXT,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


DROP TABLE IF EXISTS MESSAGES CASCADE;
CREATE TABLE MESSAGES (
	message_id SERIAL PRIMARY KEY,
	group_name VARCHAR(25),
	members TEXT,
	sender_id int REFERENCES SALON_USER(user_id),
    sender_username VARCHAR(25) NOT NULL,
	time_sent TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	contents TEXT
);

INSERT INTO MESSAGES (group_name, sender_id, sender_username, members , contents)
VALUES
('rix_andrew_nasr',  7, 'rix', 'rix, andrew' ,'Hi Andrew!');

INSERT INTO MESSAGES (group_name, sender_id, sender_username, members , contents)
VALUES
('rix_andrew_nasr', 7, 'rix', 'andrew, rix', 'How are you going?');

INSERT INTO MESSAGES (group_name, sender_id, sender_username, members , contents)
VALUES
('FunTime',  6, 'alexander', 'alexander, rix' ,'Hi Rix!');

INSERT INTO MESSAGES (group_name, sender_id, sender_username, members , contents)
VALUES
('FunTime',  6, 'alexander', 'alexander, rix, nasr' ,'Hi Nasr!');

INSERT INTO MESSAGES (group_name, sender_id, sender_username, members , contents)
VALUES
('FunTime',  6, 'alexander', 'alexander, rix, nasr, andrew' ,'Hi Andrew!');

INSERT INTO MESSAGES (group_name, sender_id, sender_username, members , contents)
VALUES
('FunTime',  7, 'rix', 'alexander, rix, nasr, andrew' ,'Thanks for the invitation!');

INSERT INTO MESSAGES (group_name, sender_id, sender_username, members , contents)
VALUES
('FunTime',  5, 'andrew', 'alexander, rix, nasr, andrew' ,'Thanks you!');

INSERT INTO MESSAGES (group_name, sender_id, sender_username, members , contents)
VALUES
('rix_andrew_nasr',  5, 'andrew', 'rix, andrew, nasr' ,'I am going well Rix! What about you Nasr?');
