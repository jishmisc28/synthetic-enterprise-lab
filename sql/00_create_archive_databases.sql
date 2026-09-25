-- First-boot only, on postgres-archive.
-- Dedicated SoR instances (lms / coll / gold / gl) create their own database
-- via POSTGRES_DB. Do not create those four here.
CREATE DATABASE aarohan_pay OWNER aarohan;
CREATE DATABASE aarohan_bureau OWNER aarohan;
CREATE DATABASE aarohan_veh OWNER aarohan;
CREATE DATABASE aarohan_crm OWNER aarohan;
CREATE DATABASE aarohan_masters OWNER aarohan;
