CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  email TEXT,
  password_hash TEXT,
  roles TEXT[] NOT NULL DEFAULT '{customer}',
  zone_id TEXT,
  address TEXT,
  lat NUMERIC(9,6),
  lng NUMERIC(9,6),
  profile_image TEXT,
  vehicle TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  admin_username TEXT UNIQUE,
  anonymized BOOLEAN NOT NULL DEFAULT FALSE,
  deleted_at TIMESTAMPTZ,
  joined TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_phone_key;
DROP INDEX IF EXISTS users_email_unique_idx;
CREATE UNIQUE INDEX IF NOT EXISTS users_customer_phone_unique_idx ON users (phone) WHERE phone IS NOT NULL AND roles @> ARRAY['customer']::text[] AND status <> 'DELETED';
CREATE UNIQUE INDEX IF NOT EXISTS users_tailor_phone_unique_idx ON users (phone) WHERE phone IS NOT NULL AND roles @> ARRAY['tailor']::text[] AND status <> 'DELETED';
CREATE UNIQUE INDEX IF NOT EXISTS users_admin_phone_unique_idx ON users (phone) WHERE phone IS NOT NULL AND roles @> ARRAY['admin']::text[] AND status <> 'DELETED';
CREATE UNIQUE INDEX IF NOT EXISTS users_customer_email_unique_idx ON users (lower(email)) WHERE email IS NOT NULL AND roles @> ARRAY['customer']::text[] AND status <> 'DELETED';
CREATE UNIQUE INDEX IF NOT EXISTS users_tailor_email_unique_idx ON users (lower(email)) WHERE email IS NOT NULL AND roles @> ARRAY['tailor']::text[] AND status <> 'DELETED';
CREATE UNIQUE INDEX IF NOT EXISTS users_admin_email_unique_idx ON users (lower(email)) WHERE email IS NOT NULL AND roles @> ARRAY['admin']::text[] AND status <> 'DELETED';
CREATE INDEX IF NOT EXISTS users_status_idx ON users(status);

CREATE TABLE IF NOT EXISTS tailors (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  shop TEXT NOT NULL,
  owner_name TEXT NOT NULL,
  zone_id TEXT NOT NULL,
  shop_address TEXT,
  lat NUMERIC(9,6),
  lng NUMERIC(9,6),
  profile_image TEXT,
  expertise TEXT[] NOT NULL DEFAULT '{}',
  years INTEGER NOT NULL DEFAULT 1,
  working_hours TEXT DEFAULT '10:00-20:00',
  bio TEXT,
  portfolio TEXT[] NOT NULL DEFAULT '{}',
  documents JSONB NOT NULL DEFAULT '{}',
  rating NUMERIC(3,2) NOT NULL DEFAULT 0,
  rating_count INTEGER NOT NULL DEFAULT 0,
  completed INTEGER NOT NULL DEFAULT 0,
  on_time_pct INTEGER NOT NULL DEFAULT 100,
  response_mins INTEGER NOT NULL DEFAULT 20,
  approval_status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
  verified BOOLEAN NOT NULL DEFAULT FALSE,
  account_status TEXT NOT NULL DEFAULT 'ACTIVE',
  reject_reason TEXT,
  availability TEXT NOT NULL DEFAULT 'AVAILABLE',
  available_slots INTEGER NOT NULL DEFAULT 5,
  max_new_orders INTEGER NOT NULL DEFAULT 5,
  next_available DATE,
  availability_note TEXT,
  accepting_requests BOOLEAN NOT NULL DEFAULT TRUE,
  availability_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
  plan TEXT NOT NULL DEFAULT 'free',
  featured BOOLEAN NOT NULL DEFAULT FALSE,
  deleted_at TIMESTAMPTZ,
  created TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tailors_visible_idx ON tailors(approval_status, account_status);
CREATE INDEX IF NOT EXISTS tailors_user_idx ON tailors(user_id);

CREATE TABLE IF NOT EXISTS tailor_services (
  id TEXT PRIMARY KEY,
  tailor_id TEXT NOT NULL REFERENCES tailors(id),
  garment_id TEXT,
  name TEXT NOT NULL,
  description TEXT,
  price INTEGER NOT NULL,
  days INTEGER NOT NULL DEFAULT 5,
  active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS services_tailor_idx ON tailor_services(tailor_id);

CREATE SEQUENCE IF NOT EXISTS requirement_code_seq START 1001;
CREATE SEQUENCE IF NOT EXISTS order_code_seq START 5001;

CREATE TABLE IF NOT EXISTS booking_requirements (
  id TEXT PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  customer_id TEXT NOT NULL REFERENCES users(id),
  garment_id TEXT,
  service_name TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  requirements TEXT,
  preferred_date DATE,
  instructions TEXT,
  measurement_mode TEXT NOT NULL DEFAULT 'SHOP',
  address TEXT,
  lat NUMERIC(9,6),
  lng NUMERIC(9,6),
  visit_date DATE,
  visit_slot TEXT,
  visit_notes TEXT,
  status TEXT NOT NULL DEFAULT 'OPEN',
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS booking_requests (
  id TEXT PRIMARY KEY,
  requirement_id TEXT NOT NULL REFERENCES booking_requirements(id),
  tailor_id TEXT NOT NULL REFERENCES tailors(id),
  service_id TEXT REFERENCES tailor_services(id),
  quoted_price INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'PENDING',
  reject_reason TEXT,
  responded_at TIMESTAMPTZ,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (requirement_id, tailor_id)
);

CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  requirement_id TEXT REFERENCES booking_requirements(id),
  request_id TEXT REFERENCES booking_requests(id),
  customer_id TEXT NOT NULL REFERENCES users(id),
  tailor_id TEXT NOT NULL REFERENCES tailors(id),
  service_id TEXT REFERENCES tailor_services(id),
  service_name TEXT NOT NULL,
  garment_id TEXT,
  quantity INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'ACCEPTED',
  base_price INTEGER NOT NULL,
  additional_total INTEGER NOT NULL DEFAULT 0,
  total INTEGER NOT NULL,
  payment_status TEXT NOT NULL DEFAULT 'PENDING',
  measurement_mode TEXT NOT NULL DEFAULT 'SHOP',
  appointment_date DATE,
  appointment_slot TEXT,
  address TEXT,
  expected_completion DATE,
  notes TEXT,
  delay_reason TEXT,
  otp_verified BOOLEAN NOT NULL DEFAULT FALSE,
  cancel_reason TEXT,
  rated BOOLEAN NOT NULL DEFAULT FALSE,
  delivered_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS orders_customer_idx ON orders(customer_id);
CREATE INDEX IF NOT EXISTS orders_tailor_idx ON orders(tailor_id);
CREATE INDEX IF NOT EXISTS orders_status_idx ON orders(status);

CREATE TABLE IF NOT EXISTS order_status_history (
  id BIGSERIAL PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(id),
  status TEXT NOT NULL,
  note TEXT,
  by_role TEXT,
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS additional_charges (
  id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(id),
  description TEXT NOT NULL,
  reason TEXT,
  amount INTEGER NOT NULL,
  added_by TEXT,
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payments (
  id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(id),
  amount INTEGER NOT NULL,
  method TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',
  txn_ref TEXT,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reviews (
  id TEXT PRIMARY KEY,
  order_id TEXT UNIQUE NOT NULL REFERENCES orders(id),
  tailor_id TEXT NOT NULL REFERENCES tailors(id),
  customer_id TEXT NOT NULL REFERENCES users(id),
  rating NUMERIC(2,1) NOT NULL,
  stars JSONB NOT NULL DEFAULT '{}',
  body TEXT,
  images TEXT[] NOT NULL DEFAULT '{}',
  hidden BOOLEAN NOT NULL DEFAULT FALSE,
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer_favorite_tailors (
  customer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tailor_id TEXT NOT NULL REFERENCES tailors(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (customer_id, tailor_id)
);
CREATE INDEX IF NOT EXISTS customer_favorite_tailors_tailor_idx ON customer_favorite_tailors(tailor_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tailor_followers (
  customer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tailor_id TEXT NOT NULL REFERENCES tailors(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (customer_id, tailor_id)
);
CREATE INDEX IF NOT EXISTS tailor_followers_tailor_idx ON tailor_followers(tailor_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tailor_offers (
  id TEXT PRIMARY KEY,
  tailor_id TEXT NOT NULL REFERENCES tailors(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  discount TEXT,
  media_url TEXT,
  media_type TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  expires_at DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tailor_offers_tailor_idx ON tailor_offers(tailor_id, active, created_at DESC);

CREATE TABLE IF NOT EXISTS complaints (
  id TEXT PRIMARY KEY,
  order_id TEXT REFERENCES orders(id),
  raised_by TEXT NOT NULL REFERENCES users(id),
  role TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  resolution TEXT,
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE SEQUENCE IF NOT EXISTS support_ticket_code_seq START 9001;

CREATE TABLE IF NOT EXISTS support_tickets (
  id TEXT PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  requester_id TEXT NOT NULL REFERENCES users(id),
  requester_role TEXT NOT NULL,
  category TEXT NOT NULL,
  subject TEXT NOT NULL,
  description TEXT NOT NULL,
  priority TEXT NOT NULL DEFAULT 'NORMAL',
  status TEXT NOT NULL DEFAULT 'OPEN',
  source TEXT NOT NULL DEFAULT 'WEB',
  order_id TEXT REFERENCES orders(id),
  assigned_to TEXT REFERENCES users(id),
  tags TEXT[] NOT NULL DEFAULT '{}',
  first_response_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  closed_at TIMESTAMPTZ,
  last_customer_reply_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_agent_reply_at TIMESTAMPTZ,
  last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS support_tickets_requester_idx ON support_tickets(requester_id, requester_role);
CREATE INDEX IF NOT EXISTS support_tickets_status_idx ON support_tickets(status, priority, last_activity_at DESC);

CREATE TABLE IF NOT EXISTS support_messages (
  id BIGSERIAL PRIMARY KEY,
  ticket_id TEXT NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
  author_id TEXT REFERENCES users(id),
  author_name TEXT NOT NULL,
  author_role TEXT NOT NULL,
  body TEXT NOT NULL,
  internal BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS support_messages_ticket_idx ON support_messages(ticket_id, created_at);

CREATE TABLE IF NOT EXISTS notifications (
  id TEXT PRIMARY KEY,
  to_ref TEXT NOT NULL,
  channel TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  read BOOLEAN NOT NULL DEFAULT FALSE,
  order_id TEXT REFERENCES orders(id),
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  admin_id TEXT REFERENCES users(id),
  admin_name TEXT,
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  target_name TEXT,
  reason TEXT,
  meta JSONB,
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS audit_ts_idx ON audit_logs(ts DESC);

-- Legacy plaintext OTP tables are intentionally not created anymore.
-- All auth, verification, and delivery OTPs use hashed otp_verifications below.

CREATE TABLE IF NOT EXISTS platform_config (
  id INTEGER PRIMARY KEY DEFAULT 1,
  commission_pct INTEGER NOT NULL DEFAULT 12,
  platform_fee INTEGER NOT NULL DEFAULT 15,
  delivery_fee INTEGER NOT NULL DEFAULT 49,
  home_visit_fee INTEGER NOT NULL DEFAULT 99,
  CONSTRAINT config_singleton CHECK (id = 1)
);
INSERT INTO platform_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Build step 01: full database schema additions.
-- These additions are intentionally additive because this app already has
-- working users, tailors, bookings, orders, notifications, and support tables.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
  CREATE TYPE tailor_registration_status AS ENUM ('pending_verification', 'active', 'suspended');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE wallet_transaction_type AS ENUM ('credit', 'debit');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE wallet_transaction_status AS ENUM ('pending', 'success', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE withdrawal_destination_type AS ENUM ('bank_account', 'upi_id');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE otp_purpose AS ENUM ('registration_phone', 'registration_email', 'login', 'forgot_password');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE booking_status_type AS ENUM (
    'searching',
    'waiting_list',
    'auto_approved',
    'tailor_confirmed',
    'measurement_pending',
    'measurement_done',
    'in_progress',
    'ready_for_delivery',
    'out_for_delivery',
    'payment_pending',
    'paid',
    'delivered',
    'completed',
    'disputed',
    'cancelled'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE booking_measurement_mode AS ENUM ('tailor_visits_customer', 'customer_visits_tailor');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE booking_tracker_stage AS ENUM (
    'Order Placed',
    'Measurement Scheduled',
    'Measurement Done',
    'Stitching in Progress',
    'Ready for Delivery',
    'Out for Delivery',
    'Delivered'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE payment_method_selection AS ENUM ('cash', 'wallet', 'qr');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE booking_payment_status AS ENUM ('pending', 'paid', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE dispute_status_type AS ENUM ('open', 'in_review', 'resolved', 'rejected');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE admin_wallet_transaction_type AS ENUM ('commission', 'gst_platform_charge');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE tailors ADD COLUMN IF NOT EXISTS tailor_id UUID;
UPDATE tailors SET tailor_id = gen_random_uuid() WHERE tailor_id IS NULL;
ALTER TABLE tailors ALTER COLUMN tailor_id SET DEFAULT gen_random_uuid();
ALTER TABLE tailors ALTER COLUMN tailor_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS tailors_tailor_id_unique_idx ON tailors(tailor_id);

ALTER TABLE tailors ADD COLUMN IF NOT EXISTS full_name VARCHAR(160);
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS phone_number VARCHAR(10);
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS dob DATE;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS aadhaar_number_hash VARCHAR(128);
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS aadhaar_number_encrypted TEXT;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS aadhaar_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS username VARCHAR(80);
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS experience_years_base NUMERIC(5,2) NOT NULL DEFAULT 0;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS stitching_since_date DATE;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS experience_display NUMERIC(5,2);
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS referral_code VARCHAR(40);
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS referred_by_tailor_id UUID;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS is_available BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS status tailor_registration_status NOT NULL DEFAULT 'pending_verification';
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
ALTER TABLE tailors ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

UPDATE tailors SET full_name = COALESCE(full_name, owner_name) WHERE full_name IS NULL;
UPDATE tailors SET created_at = COALESCE(created_at, created, now()) WHERE created_at IS NULL;
UPDATE tailors t SET phone_number = u.phone
FROM users u
WHERE t.user_id = u.id AND t.phone_number IS NULL AND u.phone ~ '^[6-9][0-9]{9}$';
UPDATE tailors t SET email = u.email
FROM users u
WHERE t.user_id = u.id AND t.email IS NULL AND u.email IS NOT NULL;

DROP INDEX IF EXISTS tailors_phone_number_unique_idx;
DROP INDEX IF EXISTS tailors_email_unique_idx;
CREATE UNIQUE INDEX IF NOT EXISTS tailors_phone_number_unique_idx ON tailors(phone_number) WHERE phone_number IS NOT NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS tailors_email_unique_idx ON tailors(lower(email)) WHERE email IS NOT NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS tailors_aadhaar_hash_unique_idx ON tailors(aadhaar_number_hash) WHERE aadhaar_number_hash IS NOT NULL;
DROP INDEX IF EXISTS tailors_username_unique_idx;
DROP INDEX IF EXISTS tailors_referral_code_unique_idx;
CREATE UNIQUE INDEX IF NOT EXISTS tailors_username_unique_idx ON tailors(username) WHERE username IS NOT NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS tailors_referral_code_unique_idx ON tailors(referral_code) WHERE referral_code IS NOT NULL AND deleted_at IS NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tailors_phone_number_format_chk') THEN
    ALTER TABLE tailors ADD CONSTRAINT tailors_phone_number_format_chk
      CHECK (phone_number IS NULL OR phone_number ~ '^[6-9][0-9]{9}$');
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tailors_referred_by_tailor_fk') THEN
    ALTER TABLE tailors ADD CONSTRAINT tailors_referred_by_tailor_fk
      FOREIGN KEY (referred_by_tailor_id) REFERENCES tailors(tailor_id);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS tailor_locations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tailor_id UUID NOT NULL REFERENCES tailors(tailor_id) ON DELETE CASCADE,
  address_text TEXT,
  latitude NUMERIC(10,7),
  longitude NUMERIC(10,7),
  is_fixed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tailor_locations_tailor_idx ON tailor_locations(tailor_id);

CREATE TABLE IF NOT EXISTS tailor_wallets (
  wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tailor_id UUID NOT NULL UNIQUE REFERENCES tailors(tailor_id) ON DELETE CASCADE,
  upi_id VARCHAR(160),
  bank_account_number TEXT,
  bank_ifsc VARCHAR(20),
  qr_code_url TEXT,
  balance NUMERIC(12,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS wallet_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_id UUID NOT NULL REFERENCES tailor_wallets(wallet_id) ON DELETE CASCADE,
  type wallet_transaction_type NOT NULL,
  amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
  reference_booking_id TEXT,
  status wallet_transaction_status NOT NULL DEFAULT 'pending',
  withdrawal_destination withdrawal_destination_type,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS wallet_transactions_wallet_idx ON wallet_transactions(wallet_id, created_at DESC);

CREATE TABLE IF NOT EXISTS referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_tailor_id UUID NOT NULL REFERENCES tailors(tailor_id) ON DELETE CASCADE,
  referred_tailor_id UUID NOT NULL REFERENCES tailors(tailor_id) ON DELETE CASCADE,
  referral_code_used VARCHAR(40) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS referrals_referrer_idx ON referrals(referrer_tailor_id);
CREATE INDEX IF NOT EXISTS referrals_referred_idx ON referrals(referred_tailor_id);

ALTER TABLE tailor_services ADD COLUMN IF NOT EXISTS service_id UUID;
UPDATE tailor_services SET service_id = gen_random_uuid() WHERE service_id IS NULL;
ALTER TABLE tailor_services ALTER COLUMN service_id SET DEFAULT gen_random_uuid();
ALTER TABLE tailor_services ALTER COLUMN service_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS tailor_services_service_id_unique_idx ON tailor_services(service_id);
ALTER TABLE tailor_services ADD COLUMN IF NOT EXISTS service_name VARCHAR(160);
ALTER TABLE tailor_services ADD COLUMN IF NOT EXISTS category VARCHAR(80);
ALTER TABLE tailor_services ADD COLUMN IF NOT EXISTS is_combo BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE tailor_services ADD COLUMN IF NOT EXISTS combo_items JSONB;
ALTER TABLE tailor_services ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE tailor_services ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE tailor_services ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
UPDATE tailor_services SET service_name = COALESCE(service_name, name) WHERE service_name IS NULL;
UPDATE tailor_services SET is_active = active WHERE is_active IS DISTINCT FROM active;

CREATE TABLE IF NOT EXISTS otp_verifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  target VARCHAR(255) NOT NULL,
  otp_hash VARCHAR(255) NOT NULL,
  purpose otp_purpose NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  verified BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS otp_verifications_target_idx ON otp_verifications(target, purpose, expires_at DESC);
ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS refresh_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(128) NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  replaced_by_token_hash VARCHAR(128),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS refresh_sessions_user_idx ON refresh_sessions(user_id, expires_at DESC);
CREATE INDEX IF NOT EXISTS refresh_sessions_active_idx ON refresh_sessions(token_hash) WHERE revoked_at IS NULL;

-- Customer identity stays on the existing role-based `users` table.
-- Do not create a parallel `customers` table for this app.
ALTER TABLE users ADD COLUMN IF NOT EXISTS customer_id UUID;
UPDATE users SET customer_id = gen_random_uuid() WHERE customer_id IS NULL;
ALTER TABLE users ALTER COLUMN customer_id SET DEFAULT gen_random_uuid();
ALTER TABLE users ALTER COLUMN customer_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS users_customer_id_unique_idx ON users(customer_id);

ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(40);
ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by_customer_id UUID;
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS users_referral_code_unique_idx ON users(referral_code) WHERE referral_code IS NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_referred_by_customer_fk') THEN
    ALTER TABLE users ADD CONSTRAINT users_referred_by_customer_fk
      FOREIGN KEY (referred_by_customer_id) REFERENCES users(customer_id);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS customer_wallets (
  wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID NOT NULL UNIQUE REFERENCES users(customer_id) ON DELETE CASCADE,
  balance NUMERIC(12,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer_referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_customer_id UUID NOT NULL REFERENCES users(customer_id) ON DELETE CASCADE,
  referred_customer_id UUID REFERENCES users(customer_id) ON DELETE SET NULL,
  referred_phone_number VARCHAR(10) NOT NULL,
  is_valid BOOLEAN NOT NULL DEFAULT TRUE,
  bonus_amount NUMERIC(12,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT customer_referrals_phone_format_chk CHECK (referred_phone_number ~ '^[6-9][0-9]{9}$')
);
CREATE INDEX IF NOT EXISTS customer_referrals_referrer_idx ON customer_referrals(referrer_customer_id);

-- Booking/order state stays on existing `orders`, `booking_requests`,
-- and `booking_requirements`. Do not create a parallel `bookings` table.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS tracker_stage booking_tracker_stage NOT NULL DEFAULT 'Order Placed';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method_selected payment_method_selection;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method_selected_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS commission_amount NUMERIC(12,2) NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS gst_platform_charge_amount NUMERIC(12,2) NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS dispute_raised BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS measurement_done_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS cloth_collected_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_address TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_lat NUMERIC(10,7);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_lng NUMERIC(10,7);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_confirmed_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_otp_expires_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS disputes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  customer_id TEXT NOT NULL REFERENCES users(id),
  reason TEXT NOT NULL,
  photo_url TEXT,
  photo_name TEXT,
  photo_media_type TEXT,
  status dispute_status_type NOT NULL DEFAULT 'open',
  resolution_notes TEXT,
  refund_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS disputes_booking_idx ON disputes(booking_id);
CREATE INDEX IF NOT EXISTS disputes_customer_idx ON disputes(customer_id);

ALTER TABLE disputes ADD COLUMN IF NOT EXISTS photo_url TEXT;
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS photo_name TEXT;
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS photo_media_type TEXT;
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS resolution_notes TEXT;
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS refund_amount NUMERIC(12,2) NOT NULL DEFAULT 0;
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS admin_wallet (
  wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  balance NUMERIC(12,2) NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admin_wallet_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type admin_wallet_transaction_type NOT NULL,
  amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
  source_booking_id TEXT NOT NULL REFERENCES orders(id),
  source_tailor_id UUID REFERENCES tailors(tailor_id),
  source_customer_id TEXT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS admin_wallet_transactions_booking_idx ON admin_wallet_transactions(source_booking_id);

CREATE TABLE IF NOT EXISTS platform_settings (
  id INTEGER PRIMARY KEY DEFAULT 1,
  commission_percentage NUMERIC(5,2) NOT NULL DEFAULT 20.00,
  gst_percentage NUMERIC(5,2) NOT NULL DEFAULT 18.00,
  platform_fee_percentage NUMERIC(5,2) NOT NULL DEFAULT 2.00,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by_admin_id UUID,
  CONSTRAINT platform_settings_singleton_chk CHECK (id = 1)
);
INSERT INTO platform_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Build step 01b: reconciliation.
-- File 01's spec described a parallel `customers` identity and a parallel
-- `bookings` table. This app already has `users` (role-based) and
-- `orders`/`booking_requirements`/`booking_requests`. Rather than run two
-- disconnected schemas, fold the new concepts into the existing tables
-- (same approach already used above for `tailors`) and retarget satellite
-- tables onto the real tables instead.

ALTER TYPE otp_purpose ADD VALUE IF NOT EXISTS 'delivery';
ALTER TYPE otp_purpose ADD VALUE IF NOT EXISTS 'withdrawal';

-- users: give every user a stable UUID "customer identity", mirroring
-- tailors.tailor_id, plus the customer-side referral/terms fields.
ALTER TABLE users ADD COLUMN IF NOT EXISTS customer_id UUID;
UPDATE users SET customer_id = gen_random_uuid() WHERE customer_id IS NULL;
ALTER TABLE users ALTER COLUMN customer_id SET DEFAULT gen_random_uuid();
ALTER TABLE users ALTER COLUMN customer_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS users_customer_id_unique_idx ON users(customer_id);

ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(40);
ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by_customer_id UUID;
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS users_referral_code_unique_idx ON users(referral_code) WHERE referral_code IS NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_referred_by_customer_fk') THEN
    ALTER TABLE users ADD CONSTRAINT users_referred_by_customer_fk
      FOREIGN KEY (referred_by_customer_id) REFERENCES users(customer_id);
  END IF;
END $$;

-- orders: absorb the tracker/delivery-payment/commission/GST/dispute/
-- precise-home-location columns file 01 put on the parallel `bookings`
-- table. `otp_verified`/`delivered_at`/`completed_at` already exist and
-- play the role of `delivery_otp_verified`/booking's delivered/completed
-- timestamps, so they are reused rather than duplicated.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS tracker_stage booking_tracker_stage NOT NULL DEFAULT 'Order Placed';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method_selected payment_method_selection;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method_selected_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS commission_amount NUMERIC(12,2) NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS gst_platform_charge_amount NUMERIC(12,2) NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS dispute_raised BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS measurement_done_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS cloth_collected_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_address TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_lat NUMERIC(10,7);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_lng NUMERIC(10,7);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_confirmed_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_otp_expires_at TIMESTAMPTZ;

-- booking_requests: allow a request against a currently-unavailable tailor
-- to be parked instead of rejected outright, for the tailor to confirm
-- later (file 15's waiting-list/tailor-priority rule). No column needed
-- ('status' is already free-text TEXT) -- application code adds the new
-- 'WAITING_LIST' value to its accepted-status set.

-- Retarget satellite tables that pointed at `customers`/`bookings` (both
-- about to be dropped, both still empty/unreferenced by the app) onto the
-- equivalent real tables. Old auto-named constraints are dropped and
-- replaced under a new name so this block is idempotent across restarts.
ALTER TABLE customer_wallets DROP CONSTRAINT IF EXISTS customer_wallets_customer_id_fkey;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'customer_wallets_customer_id_users_fkey') THEN
    ALTER TABLE customer_wallets ADD CONSTRAINT customer_wallets_customer_id_users_fkey
      FOREIGN KEY (customer_id) REFERENCES users(customer_id) ON DELETE CASCADE;
  END IF;
END $$;

ALTER TABLE customer_referrals DROP CONSTRAINT IF EXISTS customer_referrals_referrer_customer_id_fkey;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'customer_referrals_referrer_customer_id_users_fkey') THEN
    ALTER TABLE customer_referrals ADD CONSTRAINT customer_referrals_referrer_customer_id_users_fkey
      FOREIGN KEY (referrer_customer_id) REFERENCES users(customer_id) ON DELETE CASCADE;
  END IF;
END $$;
ALTER TABLE customer_referrals DROP CONSTRAINT IF EXISTS customer_referrals_referred_customer_id_fkey;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'customer_referrals_referred_customer_id_users_fkey') THEN
    ALTER TABLE customer_referrals ADD CONSTRAINT customer_referrals_referred_customer_id_users_fkey
      FOREIGN KEY (referred_customer_id) REFERENCES users(customer_id) ON DELETE SET NULL;
  END IF;
END $$;

ALTER TABLE disputes DROP CONSTRAINT IF EXISTS disputes_booking_id_fkey;
ALTER TABLE disputes ALTER COLUMN booking_id TYPE TEXT USING booking_id::text;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'disputes_booking_id_orders_fkey') THEN
    ALTER TABLE disputes ADD CONSTRAINT disputes_booking_id_orders_fkey
      FOREIGN KEY (booking_id) REFERENCES orders(id) ON DELETE CASCADE;
  END IF;
END $$;
ALTER TABLE disputes DROP CONSTRAINT IF EXISTS disputes_customer_id_fkey;
ALTER TABLE disputes ALTER COLUMN customer_id TYPE TEXT USING customer_id::text;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'disputes_customer_id_users_fkey') THEN
    ALTER TABLE disputes ADD CONSTRAINT disputes_customer_id_users_fkey
      FOREIGN KEY (customer_id) REFERENCES users(id);
  END IF;
END $$;

ALTER TABLE admin_wallet_transactions DROP CONSTRAINT IF EXISTS admin_wallet_transactions_source_booking_id_fkey;
ALTER TABLE admin_wallet_transactions ALTER COLUMN source_booking_id TYPE TEXT USING source_booking_id::text;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'admin_wallet_tx_source_booking_orders_fkey') THEN
    ALTER TABLE admin_wallet_transactions ADD CONSTRAINT admin_wallet_tx_source_booking_orders_fkey
      FOREIGN KEY (source_booking_id) REFERENCES orders(id);
  END IF;
END $$;
ALTER TABLE admin_wallet_transactions DROP CONSTRAINT IF EXISTS admin_wallet_transactions_source_customer_id_fkey;
ALTER TABLE admin_wallet_transactions ALTER COLUMN source_customer_id TYPE TEXT USING source_customer_id::text;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'admin_wallet_tx_source_customer_users_fkey') THEN
    ALTER TABLE admin_wallet_transactions ADD CONSTRAINT admin_wallet_tx_source_customer_users_fkey
      FOREIGN KEY (source_customer_id) REFERENCES users(id);
  END IF;
END $$;

ALTER TABLE wallet_transactions ALTER COLUMN reference_booking_id TYPE TEXT USING reference_booking_id::text;
ALTER TABLE payments ALTER COLUMN amount TYPE NUMERIC(12,2) USING amount::numeric;

-- Do not drop legacy/accidental `bookings` or `customers` tables here.
-- Keeping this schema non-destructive protects any local data while the
-- real app continues to use users/orders as the PostgreSQL source of truth.

-- Manual WhatsApp/admin-verified payment flow.
DO $$ BEGIN
  CREATE TYPE payment_intent_status AS ENUM ('pending', 'verified', 'expired', 'rejected', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE withdrawal_request_status AS ENUM ('pending_admin_review', 'approved', 'rejected', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS payment_intents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  customer_id TEXT NOT NULL REFERENCES users(id),
  tailor_id TEXT NOT NULL REFERENCES tailors(id),
  payment_reference TEXT UNIQUE NOT NULL,
  method TEXT NOT NULL DEFAULT 'manual_whatsapp',
  order_amount NUMERIC(12,2) NOT NULL,
  gst_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  platform_fee_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  gst_platform_charge_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  commission_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  tailor_credit_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  payable_total NUMERIC(12,2) NOT NULL,
  status payment_intent_status NOT NULL DEFAULT 'pending',
  whatsapp_url TEXT,
  admin_whatsapp_number TEXT,
  admin_upi_id TEXT,
  admin_qr_url TEXT,
  customer_note TEXT,
  admin_note TEXT,
  proof_reference TEXT,
  expires_at TIMESTAMPTZ NOT NULL,
  verified_at TIMESTAMPTZ,
  verified_by_admin_id TEXT REFERENCES users(id),
  rejected_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS payment_intents_booking_idx ON payment_intents(booking_id, created_at DESC);
CREATE INDEX IF NOT EXISTS payment_intents_status_idx ON payment_intents(status, expires_at);

CREATE TABLE IF NOT EXISTS withdrawal_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_id UUID NOT NULL REFERENCES tailor_wallets(wallet_id) ON DELETE CASCADE,
  tailor_id UUID NOT NULL REFERENCES tailors(tailor_id) ON DELETE CASCADE,
  amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  destination_type withdrawal_destination_type NOT NULL,
  destination_upi_id TEXT,
  destination_bank_account_number TEXT,
  destination_bank_ifsc VARCHAR(20),
  status withdrawal_request_status NOT NULL DEFAULT 'pending_admin_review',
  admin_note TEXT,
  payout_reference TEXT,
  otp_verified_at TIMESTAMPTZ,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  approved_at TIMESTAMPTZ,
  approved_by_admin_id TEXT REFERENCES users(id),
  rejected_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS withdrawal_requests_tailor_idx ON withdrawal_requests(tailor_id, requested_at DESC);
CREATE INDEX IF NOT EXISTS withdrawal_requests_status_idx ON withdrawal_requests(status, requested_at DESC);
