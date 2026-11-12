ALTER SESSION SET CURRENT_SCHEMA = src_erp;

INSERT INTO customers (customer_code, full_name, email, segment, country_code, city, created_at, updated_at) VALUES
('CUST-1001', 'Aarav Mehta', 'aarav.mehta@example.com', 'ENTERPRISE', 'IN', 'Bengaluru', TIMESTAMP '2026-11-01 09:15:00', TIMESTAMP '2026-11-01 09:15:00');
INSERT INTO customers (customer_code, full_name, email, segment, country_code, city, created_at, updated_at) VALUES
('CUST-1002', 'Elena Rostova', 'elena.rostova@example.com', 'SMB', 'DE', 'Berlin', TIMESTAMP '2026-11-02 11:30:00', TIMESTAMP '2026-11-02 11:30:00');
INSERT INTO customers (customer_code, full_name, email, segment, country_code, city, created_at, updated_at) VALUES
('CUST-1003', 'Marcus Vance', 'marcus.vance@example.com', 'RETAIL', 'US', 'Austin', TIMESTAMP '2026-11-03 14:20:00', TIMESTAMP '2026-11-03 14:20:00');
INSERT INTO customers (customer_code, full_name, email, segment, country_code, city, created_at, updated_at) VALUES
('CUST-1004', 'Priya Nair', 'priya.nair@example.com', 'ENTERPRISE', 'IN', 'Mumbai', TIMESTAMP '2026-11-05 16:45:00', TIMESTAMP '2026-11-05 16:45:00');
INSERT INTO customers (customer_code, full_name, email, segment, country_code, city, created_at, updated_at) VALUES
('CUST-1005', 'Liam OConnor', 'liam.oconnor@example.com', 'SMB', 'GB', 'London', TIMESTAMP '2026-11-08 10:05:00', TIMESTAMP '2026-11-08 10:05:00');

INSERT INTO products (sku, product_name, category, unit_price, unit_cost, created_at, updated_at) VALUES
('SKU-CLOUD-01', 'Enterprise Edge Gateway', 'Networking', 1250.00, 620.00, TIMESTAMP '2026-11-01 08:00:00', TIMESTAMP '2026-11-01 08:00:00');
INSERT INTO products (sku, product_name, category, unit_price, unit_cost, created_at, updated_at) VALUES
('SKU-SEN-02', 'Industrial IoT Sensor Kit', 'Telemetry', 340.00, 145.00, TIMESTAMP '2026-11-01 08:05:00', TIMESTAMP '2026-11-01 08:05:00');
INSERT INTO products (sku, product_name, category, unit_price, unit_cost, created_at, updated_at) VALUES
('SKU-SRV-03', 'Rack Compute Node G4', 'Compute', 4800.00, 2900.00, TIMESTAMP '2026-11-01 08:10:00', TIMESTAMP '2026-11-01 08:10:00');
INSERT INTO products (sku, product_name, category, unit_price, unit_cost, created_at, updated_at) VALUES
('SKU-LIC-04', 'Annual Telemetry Analytics License', 'Software', 990.00, 120.00, TIMESTAMP '2026-11-01 08:15:00', TIMESTAMP '2026-11-01 08:15:00');

INSERT INTO orders (order_number, customer_id, order_status, currency_code, order_date, updated_at) VALUES
('ORD-2026-0001', 1, 'DELIVERED', 'USD', TIMESTAMP '2026-11-02 10:00:00', TIMESTAMP '2026-11-04 15:30:00');
INSERT INTO orders (order_number, customer_id, order_status, currency_code, order_date, updated_at) VALUES
('ORD-2026-0002', 2, 'SHIPPED', 'EUR', TIMESTAMP '2026-11-04 13:15:00', TIMESTAMP '2026-11-06 09:10:00');
INSERT INTO orders (order_number, customer_id, order_status, currency_code, order_date, updated_at) VALUES
('ORD-2026-0003', 3, 'DELIVERED', 'USD', TIMESTAMP '2026-11-06 17:40:00', TIMESTAMP '2026-11-08 11:20:00');
INSERT INTO orders (order_number, customer_id, order_status, currency_code, order_date, updated_at) VALUES
('ORD-2026-0004', 4, 'CONFIRMED', 'USD', TIMESTAMP '2026-11-09 09:50:00', TIMESTAMP '2026-11-09 10:15:00');
INSERT INTO orders (order_number, customer_id, order_status, currency_code, order_date, updated_at) VALUES
('ORD-2026-0005', 5, 'PENDING', 'GBP', TIMESTAMP '2026-11-11 14:25:00', TIMESTAMP '2026-11-11 14:25:00');

INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct, updated_at) VALUES
(1, 1, 2, 1250.00, 5.00, TIMESTAMP '2026-11-02 10:00:00');
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct, updated_at) VALUES
(1, 4, 2, 990.00, 0.00, TIMESTAMP '2026-11-02 10:00:00');
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct, updated_at) VALUES
(2, 2, 5, 340.00, 10.00, TIMESTAMP '2026-11-04 13:15:00');
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct, updated_at) VALUES
(3, 2, 1, 340.00, 0.00, TIMESTAMP '2026-11-06 17:40:00');
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct, updated_at) VALUES
(4, 3, 3, 4800.00, 8.00, TIMESTAMP '2026-11-09 09:50:00');
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct, updated_at) VALUES
(4, 4, 3, 990.00, 0.00, TIMESTAMP '2026-11-09 09:50:00');
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct, updated_at) VALUES
(5, 1, 1, 1250.00, 0.00, TIMESTAMP '2026-11-11 14:25:00');

COMMIT;
