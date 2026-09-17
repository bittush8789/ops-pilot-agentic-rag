-- =============================================================
-- OpsPilot — Seed Data
-- Run after CREATE TABLE statements (handled by SQLAlchemy init_db)
-- =============================================================

USE ops_workflow_db;

-- =============================================================
-- CUSTOMERS (20 records)
-- =============================================================
INSERT INTO customers (customer_id, name, email, account_status, plan, phone, company, country, created_at, updated_at) VALUES
('cust-45821', 'Rajesh Mehta',       'rajesh.mehta@techcorp.io',        'active',    'enterprise',    '+1-555-0101', 'TechCorp Solutions',    'US', NOW() - INTERVAL 2 YEAR,  NOW()),
('cust-45822', 'Sarah Williams',     'sarah.w@globalpay.com',            'active',    'professional',  '+1-555-0102', 'GlobalPay Inc',         'US', NOW() - INTERVAL 18 MONTH, NOW()),
('cust-45823', 'Marcus Johnson',     'marcus@fintech-ventures.com',      'suspended', 'professional',  '+1-555-0103', 'FinTech Ventures',      'UK', NOW() - INTERVAL 1 YEAR,  NOW()),
('cust-45824', 'Emily Chen',         'emily.chen@shopzone.net',          'active',    'starter',       '+1-555-0104', 'ShopZone Ltd',          'CA', NOW() - INTERVAL 8 MONTH, NOW()),
('cust-45825', 'David Rodriguez',    'david.r@mediastream.tv',           'active',    'professional',  '+1-555-0105', 'MediaStream TV',        'US', NOW() - INTERVAL 14 MONTH, NOW()),
('cust-45826', 'Jennifer Kim',       'jkim@logisticspro.com',            'active',    'enterprise',    '+1-555-0106', 'LogisticsPro Inc',      'US', NOW() - INTERVAL 3 YEAR,  NOW()),
('cust-45827', 'Robert Taylor',      'rtaylor@cloud9saas.com',           'active',    'starter',       '+1-555-0107', 'Cloud9 SaaS',           'AU', NOW() - INTERVAL 5 MONTH, NOW()),
('cust-45828', 'Priya Patel',        'priya.patel@healthplus.org',       'active',    'professional',  '+1-555-0108', 'HealthPlus Medical',    'US', NOW() - INTERVAL 22 MONTH, NOW()),
('cust-45829', 'Thomas Anderson',    'tanderson@securevault.io',         'active',    'enterprise',    '+1-555-0109', 'SecureVault Security',  'US', NOW() - INTERVAL 4 YEAR,  NOW()),
('cust-45830', 'Lisa Nguyen',        'lisa.n@retailhub.store',           'closed',    'starter',       '+1-555-0110', 'RetailHub Commerce',    'US', NOW() - INTERVAL 6 MONTH, NOW()),
('cust-45831', 'James Wilson',       'jwilson@automotivex.com',          'active',    'professional',  '+1-555-0111', 'AutomotiveX Corp',      'DE', NOW() - INTERVAL 16 MONTH, NOW()),
('cust-45832', 'Amanda Foster',      'afoster@edustep.edu',              'active',    'starter',       '+1-555-0112', 'EduStep Learning',      'CA', NOW() - INTERVAL 9 MONTH, NOW()),
('cust-45833', 'Carlos Mendez',      'carlos.m@legalease.law',           'active',    'professional',  '+1-555-0113', 'LegalEase Firm',        'US', NOW() - INTERVAL 11 MONTH, NOW()),
('cust-45834', 'Natalie Brown',      'nbrown@realestatepro.com',         'active',    'enterprise',    '+1-555-0114', 'RealEstate Pro',        'US', NOW() - INTERVAL 30 MONTH, NOW()),
('cust-45835', 'Kevin Zhang',        'kzhang@quantumapps.dev',           'active',    'professional',  '+1-555-0115', 'QuantumApps Dev',       'SG', NOW() - INTERVAL 7 MONTH, NOW()),
('cust-45836', 'Olivia Harris',      'oharris@fashionforward.com',       'active',    'starter',       '+1-555-0116', 'FashionForward Ltd',    'UK', NOW() - INTERVAL 4 MONTH, NOW()),
('cust-45837', 'Michael Lee',        'michael.l@constructionbase.com',   'active',    'professional',  '+1-555-0117', 'ConstructionBase Corp', 'US', NOW() - INTERVAL 19 MONTH, NOW()),
('cust-45838', 'Sophie Martin',      'sophie.m@agritech.farm',           'pending',   'free',          '+1-555-0118', 'AgriTech Innovations',  'FR', NOW() - INTERVAL 1 MONTH, NOW()),
('cust-45839', 'Ryan Thompson',      'rthompson@cybershield.io',         'active',    'enterprise',    '+1-555-0119', 'CyberShield Security',  'US', NOW() - INTERVAL 26 MONTH, NOW()),
('cust-45840', 'Angela Martinez',    'amarite@digitalwave.co',           'active',    'professional',  '+1-555-0120', 'DigitalWave Agency',    'MX', NOW() - INTERVAL 12 MONTH, NOW());

-- =============================================================
-- TICKETS (30 records)
-- =============================================================
INSERT INTO tickets (ticket_id, ticket_number, customer_id, title, description, category, priority, status, created_at, updated_at) VALUES
-- KEY TICKET: INC-1042 — Payment failures for customer 45821
('tick-1042', 'INC-1042', 'cust-45821', 'Multiple payment failures — Customer 45821',
 'Customer 45821 has experienced multiple payment failures in the last 30 minutes. Please investigate and recommend an action.',
 'payment_failure', 'high', 'open', NOW() - INTERVAL 30 MINUTE, NOW() - INTERVAL 30 MINUTE),

-- Additional realistic tickets
('tick-1043', 'INC-1043', 'cust-45822', 'Duplicate charge on account',
 'Customer reports seeing a duplicate charge of $299.00 on their statement from this morning.',
 'duplicate_payment', 'medium', 'open', NOW() - INTERVAL 2 HOUR, NOW() - INTERVAL 2 HOUR),
('tick-1044', 'INC-1044', 'cust-45823', 'Account suspended — appeal request',
 'Customer account was automatically suspended due to failed payment attempts. Customer is requesting appeal.',
 'account_issue', 'medium', 'investigating', NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 4 HOUR),
('tick-1045', 'INC-1045', 'cust-45824', 'Refund not received after 7 days',
 'Customer requested a refund 7 days ago for order #ORD-88821. Refund not yet reflected in account.',
 'refund_request', 'medium', 'open', NOW() - INTERVAL 7 DAY, NOW() - INTERVAL 7 DAY),
('tick-1046', 'INC-1046', 'cust-45825', 'Payment gateway timeout during checkout',
 'Multiple customers reporting gateway timeouts during checkout flow. Possible service degradation.',
 'payment_failure', 'critical', 'investigating', NOW() - INTERVAL 45 MINUTE, NOW() - INTERVAL 10 MINUTE),
('tick-1047', 'INC-1047', 'cust-45826', 'Invoice discrepancy — overcharged',
 'Enterprise customer claims invoice amount does not match agreed contract price.',
 'general', 'high', 'open', NOW() - INTERVAL 3 HOUR, NOW() - INTERVAL 3 HOUR),
('tick-1048', 'INC-1048', 'cust-45827', 'Card declined — valid card',
 'Customer reports their card is being declined even though it is valid and has sufficient funds.',
 'payment_failure', 'medium', 'open', NOW() - INTERVAL 5 HOUR, NOW() - INTERVAL 5 HOUR),
('tick-1049', 'INC-1049', 'cust-45828', 'Cannot login — account locked',
 'Customer account is locked after multiple failed login attempts. Requires manual unlock.',
 'account_issue', 'medium', 'resolved', NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 1 DAY),
('tick-1050', 'INC-1050', 'cust-45829', 'Suspicious transaction flagged',
 'Fraud detection flagged a transaction of $4,999.99 as suspicious. Requires review.',
 'security_alert', 'high', 'investigating', NOW() - INTERVAL 6 HOUR, NOW() - INTERVAL 2 HOUR),
('tick-1051', 'INC-1051', 'cust-45831', 'Subscription renewal failed',
 'Annual subscription renewal failed with INSUFFICIENT_FUNDS. Customer should be notified.',
 'payment_failure', 'medium', 'open', NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 1 DAY),
('tick-1052', 'INC-1052', 'cust-45832', 'PayPal payment not reflected',
 'Customer completed PayPal checkout but payment not showing in their account.',
 'payment_failure', 'medium', 'open', NOW() - INTERVAL 8 HOUR, NOW() - INTERVAL 8 HOUR),
('tick-1053', 'INC-1053', 'cust-45833', 'Wire transfer delay',
 'Wire transfer of $15,000 submitted 3 business days ago, not yet cleared.',
 'payment_failure', 'high', 'open', NOW() - INTERVAL 3 DAY, NOW() - INTERVAL 3 DAY),
('tick-1054', 'INC-1054', 'cust-45834', 'Enterprise contract renewal — manual billing',
 'Enterprise customer contract expires in 5 days, renewal needs manual billing configuration.',
 'general', 'high', 'open', NOW() - INTERVAL 5 HOUR, NOW() - INTERVAL 5 HOUR),
('tick-1055', 'INC-1055', 'cust-45835', 'API payment integration failing',
 'Customer reports their payment API integration stopped working after our SDK update.',
 'service_outage', 'high', 'open', NOW() - INTERVAL 12 HOUR, NOW() - INTERVAL 12 HOUR),
('tick-1056', 'INC-1056', 'cust-45836', 'Chargeback dispute received',
 'Received chargeback dispute from card issuer for transaction TXN-90021.',
 'general', 'medium', 'open', NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 1 DAY),
('tick-1057', 'INC-1057', 'cust-45837', 'Bulk payment file rejected',
 'Monthly bulk payment file (120 records) rejected by processor with error INVALID_FORMAT.',
 'payment_failure', 'high', 'open', NOW() - INTERVAL 4 HOUR, NOW() - INTERVAL 4 HOUR),
('tick-1058', 'INC-1058', 'cust-45839', 'Security alert — unusual login location',
 'Login detected from unusual geographic location (IP: 185.220.101.45) for enterprise account.',
 'security_alert', 'critical', 'investigating', NOW() - INTERVAL 1 HOUR, NOW() - INTERVAL 30 MINUTE),
('tick-1059', 'INC-1059', 'cust-45840', 'Bank transfer returned',
 'Bank transfer of $5,200 returned with code R03 — No Account.',
 'payment_failure', 'medium', 'open', NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 2 DAY),
('tick-1060', 'INC-1060', 'cust-45821', 'Previous payment issue — resolved reference',
 'Previous payment gateway issue for this customer from last month. Resolved for reference.',
 'payment_failure', 'medium', 'closed', NOW() - INTERVAL 30 DAY, NOW() - INTERVAL 28 DAY),
('tick-1061', 'INC-1061', 'cust-45822', 'Refund request for cancelled subscription',
 'Customer cancelled subscription mid-cycle and is requesting prorated refund.',
 'refund_request', 'low', 'open', NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 2 DAY),
('tick-1062', 'INC-1062', 'cust-45823', 'Account reactivation after payment',
 'Customer made overdue payment, account should be reactivated.',
 'account_issue', 'medium', 'resolved', NOW() - INTERVAL 5 DAY, NOW() - INTERVAL 4 DAY),
('tick-1063', 'INC-1063', 'cust-45824', 'Pricing plan upgrade payment failed',
 'Customer attempted to upgrade from starter to professional plan. Payment failed.',
 'payment_failure', 'medium', 'open', NOW() - INTERVAL 6 HOUR, NOW() - INTERVAL 6 HOUR),
('tick-1064', 'INC-1064', 'cust-45825', 'Webhook not received for payment',
 'Customer reports no webhook event received for successful payment.',
 'service_outage', 'medium', 'open', NOW() - INTERVAL 10 HOUR, NOW() - INTERVAL 10 HOUR),
('tick-1065', 'INC-1065', 'cust-45826', 'Invoice PDF not generating',
 'Customer cannot download invoice PDF for multiple transactions.',
 'general', 'low', 'open', NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 1 DAY),
('tick-1066', 'INC-1066', 'cust-45828', 'Payment success but service not activated',
 'Payment of $199 processed successfully but service subscription not activated.',
 'service_outage', 'high', 'open', NOW() - INTERVAL 3 HOUR, NOW() - INTERVAL 3 HOUR),
('tick-1067', 'INC-1067', 'cust-45829', 'Failed to charge saved card',
 'System failed to charge customers saved credit card on file for monthly subscription.',
 'payment_failure', 'medium', 'open', NOW() - INTERVAL 5 HOUR, NOW() - INTERVAL 5 HOUR),
('tick-1068', 'INC-1068', 'cust-45831', 'Payment amount mismatch',
 'Customer charged $499 but invoice shows $449. Discrepancy of $50.',
 'general', 'medium', 'open', NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 2 DAY),
('tick-1069', 'INC-1069', 'cust-45833', 'Bank declined ACH transfer',
 'ACH payment of $8,000 declined by receiving bank.',
 'payment_failure', 'high', 'open', NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 1 DAY),
('tick-1070', 'INC-1070', 'cust-45834', 'Batch invoice reconciliation mismatch',
 'Monthly batch reconciliation report shows 12 mismatched transactions.',
 'general', 'medium', 'open', NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 2 DAY),
('tick-1071', 'INC-1071', 'cust-45835', 'SDK authentication error on payment',
 'New SDK version returning auth error during payment initialization.',
 'service_outage', 'high', 'open', NOW() - INTERVAL 8 HOUR, NOW() - INTERVAL 8 HOUR);

-- =============================================================
-- TRANSACTIONS (100+ records)
-- Focus: Customer 45821 has 7 recent transactions, 5 failed
-- =============================================================

-- Customer cust-45821 — KEY SCENARIO (7 transactions, 5 failed PAYMENT_GATEWAY_TIMEOUT)
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45821-001', 'cust-45821', 1299.00, 'USD', 'failed', 'credit_card', 'PAYMENT_GATEWAY_TIMEOUT', 'stripe-v2', 'REF-2024-45821-001', NOW() - INTERVAL 28 MINUTE),
('txn-45821-002', 'cust-45821', 1299.00, 'USD', 'failed', 'credit_card', 'PAYMENT_GATEWAY_TIMEOUT', 'stripe-v2', 'REF-2024-45821-002', NOW() - INTERVAL 25 MINUTE),
('txn-45821-003', 'cust-45821', 1299.00, 'USD', 'failed', 'credit_card', 'PAYMENT_GATEWAY_TIMEOUT', 'stripe-v2', 'REF-2024-45821-003', NOW() - INTERVAL 20 MINUTE),
('txn-45821-004', 'cust-45821', 1299.00, 'USD', 'failed', 'credit_card', 'PAYMENT_GATEWAY_TIMEOUT', 'stripe-v2', 'REF-2024-45821-004', NOW() - INTERVAL 15 MINUTE),
('txn-45821-005', 'cust-45821', 1299.00, 'USD', 'failed', 'credit_card', 'PAYMENT_GATEWAY_TIMEOUT', 'stripe-v2', 'REF-2024-45821-005', NOW() - INTERVAL 10 MINUTE),
('txn-45821-006', 'cust-45821',  499.00, 'USD', 'success', 'credit_card', NULL, 'stripe-v2', 'REF-2024-45821-006', NOW() - INTERVAL 2 DAY),
('txn-45821-007', 'cust-45821', 1299.00, 'USD', 'success', 'credit_card', NULL, 'stripe-v2', 'REF-2024-45821-007', NOW() - INTERVAL 30 DAY);

-- Customer cust-45822 — duplicate payment scenario
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45822-001', 'cust-45822', 299.00, 'USD', 'success',  'credit_card', NULL,                  'stripe-v2', 'REF-45822-001', NOW() - INTERVAL 10 HOUR),
('txn-45822-002', 'cust-45822', 299.00, 'USD', 'success',  'credit_card', NULL,                  'stripe-v2', 'REF-45822-002', NOW() - INTERVAL 10 HOUR),
('txn-45822-003', 'cust-45822', 149.00, 'USD', 'success',  'credit_card', NULL,                  'stripe-v2', 'REF-45822-003', NOW() - INTERVAL 5 DAY),
('txn-45822-004', 'cust-45822', 299.00, 'USD', 'refunded', 'credit_card', NULL,                  'stripe-v2', 'REF-45822-004', NOW() - INTERVAL 3 DAY);

-- Customer cust-45823 — failed payments leading to suspension
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45823-001', 'cust-45823', 599.00, 'USD', 'failed',  'credit_card', 'INSUFFICIENT_FUNDS',  'stripe-v2', 'REF-45823-001', NOW() - INTERVAL 1 DAY),
('txn-45823-002', 'cust-45823', 599.00, 'USD', 'failed',  'credit_card', 'CARD_DECLINED',        'stripe-v2', 'REF-45823-002', NOW() - INTERVAL 2 DAY),
('txn-45823-003', 'cust-45823', 599.00, 'USD', 'failed',  'debit_card',  'INSUFFICIENT_FUNDS',  'stripe-v2', 'REF-45823-003', NOW() - INTERVAL 3 DAY),
('txn-45823-004', 'cust-45823', 599.00, 'USD', 'success', 'bank_transfer', NULL,                 'plaid',    'REF-45823-004', NOW() - INTERVAL 35 DAY);

-- Customer cust-45824
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45824-001', 'cust-45824',  49.00, 'USD', 'success', 'credit_card', NULL,               'stripe-v2', 'REF-45824-001', NOW() - INTERVAL 2 DAY),
('txn-45824-002', 'cust-45824',  99.00, 'USD', 'failed',  'credit_card', 'CARD_DECLINED',    'stripe-v2', 'REF-45824-002', NOW() - INTERVAL 6 HOUR),
('txn-45824-003', 'cust-45824',  49.00, 'USD', 'success', 'credit_card', NULL,               'stripe-v2', 'REF-45824-003', NOW() - INTERVAL 32 DAY);

-- Customer cust-45825 — payment gateway timeout
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45825-001', 'cust-45825', 299.00, 'USD', 'failed', 'credit_card', 'PAYMENT_GATEWAY_TIMEOUT', 'stripe-v2', 'REF-45825-001', NOW() - INTERVAL 40 MINUTE),
('txn-45825-002', 'cust-45825', 299.00, 'USD', 'failed', 'credit_card', 'PAYMENT_GATEWAY_TIMEOUT', 'stripe-v2', 'REF-45825-002', NOW() - INTERVAL 35 MINUTE),
('txn-45825-003', 'cust-45825', 199.00, 'USD', 'success','credit_card', NULL,                       'stripe-v2', 'REF-45825-003', NOW() - INTERVAL 7 DAY);

-- Customer cust-45826
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45826-001', 'cust-45826', 2499.00, 'USD', 'success', 'bank_transfer', NULL, 'plaid',    'REF-45826-001', NOW() - INTERVAL 3 DAY),
('txn-45826-002', 'cust-45826',  499.00, 'USD', 'success', 'credit_card',   NULL, 'stripe-v2','REF-45826-002', NOW() - INTERVAL 30 DAY),
('txn-45826-003', 'cust-45826', 2499.00, 'USD', 'success', 'bank_transfer', NULL, 'plaid',    'REF-45826-003', NOW() - INTERVAL 60 DAY);

-- Customer cust-45827
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45827-001', 'cust-45827',  49.00, 'USD', 'failed',  'credit_card', 'CARD_DECLINED',    'stripe-v2', 'REF-45827-001', NOW() - INTERVAL 5 HOUR),
('txn-45827-002', 'cust-45827',  49.00, 'USD', 'success', 'debit_card',  NULL,               'stripe-v2', 'REF-45827-002', NOW() - INTERVAL 1 DAY);

-- Customer cust-45828
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45828-001', 'cust-45828', 199.00, 'USD', 'success', 'paypal',       NULL,              'paypal',    'REF-45828-001', NOW() - INTERVAL 3 HOUR),
('txn-45828-002', 'cust-45828', 199.00, 'USD', 'success', 'credit_card',  NULL,              'stripe-v2', 'REF-45828-002', NOW() - INTERVAL 30 DAY),
('txn-45828-003', 'cust-45828', 199.00, 'USD', 'success', 'credit_card',  NULL,              'stripe-v2', 'REF-45828-003', NOW() - INTERVAL 60 DAY);

-- Customer cust-45829 — suspicious transaction
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45829-001', 'cust-45829', 4999.99, 'USD', 'pending', 'credit_card', 'FRAUD_SUSPECTED', 'stripe-v2', 'REF-45829-001', NOW() - INTERVAL 6 HOUR),
('txn-45829-002', 'cust-45829',  999.00, 'USD', 'success', 'credit_card', NULL,              'stripe-v2', 'REF-45829-002', NOW() - INTERVAL 7 DAY),
('txn-45829-003', 'cust-45829', 1299.00, 'USD', 'success', 'credit_card', NULL,              'stripe-v2', 'REF-45829-003', NOW() - INTERVAL 37 DAY);

-- Customer cust-45831 — subscription renewal failed
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45831-001', 'cust-45831', 599.00, 'USD', 'failed',  'credit_card', 'INSUFFICIENT_FUNDS', 'stripe-v2', 'REF-45831-001', NOW() - INTERVAL 1 DAY),
('txn-45831-002', 'cust-45831', 599.00, 'USD', 'success', 'credit_card', NULL,                 'stripe-v2', 'REF-45831-002', NOW() - INTERVAL 365 DAY),
('txn-45831-003', 'cust-45831', 299.00, 'USD', 'success', 'credit_card', NULL,                 'stripe-v2', 'REF-45831-003', NOW() - INTERVAL 180 DAY);

-- Customer cust-45832
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45832-001', 'cust-45832', 29.00, 'USD', 'pending', 'paypal', NULL,  'paypal', 'REF-45832-001', NOW() - INTERVAL 8 HOUR),
('txn-45832-002', 'cust-45832', 29.00, 'USD', 'success', 'paypal', NULL,  'paypal', 'REF-45832-002', NOW() - INTERVAL 30 DAY);

-- Customer cust-45833 — wire transfer
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45833-001', 'cust-45833', 15000.00, 'USD', 'pending',  'wire',          NULL,                'wire-gateway', 'REF-45833-001', NOW() - INTERVAL 3 DAY),
('txn-45833-002', 'cust-45833',  8000.00, 'USD', 'failed',   'bank_transfer', 'BANK_REJECT',       'plaid',        'REF-45833-002', NOW() - INTERVAL 1 DAY),
('txn-45833-003', 'cust-45833',  5000.00, 'USD', 'success',  'bank_transfer', NULL,                'plaid',        'REF-45833-003', NOW() - INTERVAL 30 DAY);

-- Customer cust-45834
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45834-001', 'cust-45834', 4999.00, 'USD', 'success', 'bank_transfer', NULL, 'plaid', 'REF-45834-001', NOW() - INTERVAL 5 DAY),
('txn-45834-002', 'cust-45834', 4999.00, 'USD', 'success', 'bank_transfer', NULL, 'plaid', 'REF-45834-002', NOW() - INTERVAL 35 DAY);

-- Customer cust-45835 — API issues
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45835-001', 'cust-45835', 199.00, 'USD', 'failed',  'credit_card', 'NETWORK_ERROR', 'stripe-v2', 'REF-45835-001', NOW() - INTERVAL 12 HOUR),
('txn-45835-002', 'cust-45835', 199.00, 'USD', 'failed',  'credit_card', 'NETWORK_ERROR', 'stripe-v2', 'REF-45835-002', NOW() - INTERVAL 11 HOUR),
('txn-45835-003', 'cust-45835', 199.00, 'USD', 'success', 'credit_card', NULL,            'stripe-v2', 'REF-45835-003', NOW() - INTERVAL 30 DAY);

-- Customer cust-45836
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45836-001', 'cust-45836', 79.00, 'USD', 'disputed', 'credit_card', NULL, 'stripe-v2', 'REF-45836-001', NOW() - INTERVAL 1 DAY),
('txn-45836-002', 'cust-45836', 79.00, 'USD', 'success',  'credit_card', NULL, 'stripe-v2', 'REF-45836-002', NOW() - INTERVAL 30 DAY);

-- Customer cust-45837
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45837-001', 'cust-45837', 8900.00, 'USD', 'failed',  'bank_transfer', 'BANK_REJECT', 'plaid', 'REF-45837-001', NOW() - INTERVAL 4 HOUR),
('txn-45837-002', 'cust-45837', 8900.00, 'USD', 'success', 'bank_transfer', NULL,          'plaid', 'REF-45837-002', NOW() - INTERVAL 30 DAY);

-- Customer cust-45839
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45839-001', 'cust-45839', 2499.00, 'USD', 'success', 'credit_card', NULL, 'stripe-v2', 'REF-45839-001', NOW() - INTERVAL 7 DAY),
('txn-45839-002', 'cust-45839', 2499.00, 'USD', 'success', 'credit_card', NULL, 'stripe-v2', 'REF-45839-002', NOW() - INTERVAL 37 DAY);

-- Customer cust-45840
INSERT INTO transactions (transaction_id, customer_id, amount, currency, status, payment_method, failure_reason, gateway, reference_id, created_at) VALUES
('txn-45840-001', 'cust-45840', 5200.00, 'USD', 'failed',  'bank_transfer', 'BANK_REJECT', 'plaid', 'REF-45840-001', NOW() - INTERVAL 2 DAY),
('txn-45840-002', 'cust-45840', 1200.00, 'USD', 'success', 'credit_card',   NULL,          'stripe-v2', 'REF-45840-002', NOW() - INTERVAL 30 DAY);

-- =============================================================
-- INCIDENTS (20 records)
-- =============================================================
INSERT INTO incidents (incident_id, customer_id, incident_number, category, severity, status, title, description, affected_service, root_cause, resolution, created_at, updated_at) VALUES
-- Related to cust-45821 payment failures
('inc-001', 'cust-45821', 'SINC-001', 'payment_gateway', 'high', 'open',
 'Payment gateway timeouts affecting enterprise customer',
 'Customer 45821 experiencing repeated payment gateway timeouts. 5 failed transactions in 30 minutes.',
 'stripe-payment-api', NULL, NULL,
 NOW() - INTERVAL 25 MINUTE, NOW() - INTERVAL 25 MINUTE),

-- Prior incident for same customer (historical)
('inc-002', 'cust-45821', 'SINC-002', 'payment_gateway', 'medium', 'resolved',
 'Payment gateway intermittent failures — prior incident',
 'Payment gateway experienced intermittent failures for 2 hours last month. Affected multiple enterprise customers.',
 'stripe-payment-api', 'Stripe infrastructure maintenance caused temporary degradation.',
 'Stripe resolved the issue on their end. All queued transactions processed.',
 NOW() - INTERVAL 30 DAY, NOW() - INTERVAL 29 DAY),

-- General payment gateway incident (multiple customers)
('inc-003', NULL, 'SINC-003', 'payment_gateway', 'critical', 'investigating',
 'Stripe payment API degradation — multiple customers affected',
 'Multiple customers reporting payment gateway timeouts. Stripe status page shows elevated error rates.',
 'stripe-payment-api', NULL, NULL,
 NOW() - INTERVAL 35 MINUTE, NOW() - INTERVAL 5 MINUTE),

('inc-004', 'cust-45823', 'SINC-004', 'account_lockout', 'medium', 'resolved',
 'Account suspension due to failed payment threshold',
 'Customer account automatically suspended after 3 failed payment attempts.',
 'billing-service', 'Automatic suspension policy triggered.', 'Account reactivated after manual review.',
 NOW() - INTERVAL 5 DAY, NOW() - INTERVAL 4 DAY),

('inc-005', 'cust-45825', 'SINC-005', 'payment_gateway', 'high', 'investigating',
 'Payment gateway timeouts at checkout — MediaStream TV',
 'Customer reporting checkout failures. Gateway returning 504 errors.',
 'stripe-payment-api', NULL, NULL,
 NOW() - INTERVAL 40 MINUTE, NOW() - INTERVAL 10 MINUTE),

('inc-006', 'cust-45829', 'SINC-006', 'security_breach', 'high', 'investigating',
 'Suspicious high-value transaction — possible fraud',
 'Transaction of $4,999.99 flagged by fraud detection. Unusual purchase pattern.',
 'fraud-detection-service', NULL, NULL,
 NOW() - INTERVAL 6 HOUR, NOW() - INTERVAL 1 HOUR),

('inc-007', NULL, 'SINC-007', 'service_degradation', 'medium', 'resolved',
 'Payment webhook delivery delays',
 'Webhook delivery system experiencing delays of up to 30 minutes.',
 'webhook-service', 'Queue backlog due to increased transaction volume.',
 'Queue cleared, webhook delivery back to normal.',
 NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 1 DAY),

('inc-008', 'cust-45831', 'SINC-008', 'payment_gateway', 'medium', 'open',
 'Subscription renewal failure — insufficient funds',
 'Annual subscription renewal failed. Customer card has insufficient funds.',
 'billing-service', NULL, NULL,
 NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 1 DAY),

('inc-009', NULL, 'SINC-009', 'network', 'high', 'resolved',
 'Payment API latency spike — elevated response times',
 'payment-api service showing P99 latency of 8 seconds (normal: 200ms). Caused by gateway timeouts.',
 'payment-api', 'Gateway connection pool exhausted during traffic spike.',
 'Connection pool scaled up. Latency returned to normal.',
 NOW() - INTERVAL 3 HOUR, NOW() - INTERVAL 1 HOUR),

('inc-010', NULL, 'SINC-010', 'payment_gateway', 'critical', 'mitigated',
 'Stripe gateway outage — December 2023',
 'Major Stripe gateway outage affecting all customers for 45 minutes.',
 'stripe-payment-api', 'Stripe datacenter networking issue.',
 'Stripe resolved the networking issue. Failover to backup gateway implemented.',
 NOW() - INTERVAL 90 DAY, NOW() - INTERVAL 89 DAY),

('inc-011', 'cust-45833', 'SINC-011', 'payment_gateway', 'high', 'open',
 'Wire transfer stuck in processing',
 'Large wire transfer stuck in processing state for 3 business days.',
 'wire-transfer-service', NULL, NULL,
 NOW() - INTERVAL 3 DAY, NOW() - INTERVAL 1 DAY),

('inc-012', 'cust-45835', 'SINC-012', 'service_degradation', 'high', 'open',
 'Payment SDK v4.2 authentication errors',
 'Multiple customers using SDK v4.2 reporting authentication errors during payment.',
 'payment-sdk', NULL, NULL,
 NOW() - INTERVAL 12 HOUR, NOW() - INTERVAL 2 HOUR),

('inc-013', NULL, 'SINC-013', 'payment_gateway', 'medium', 'resolved',
 'PayPal integration intermittent failures',
 'PayPal payment processing intermittently failing with timeout errors.',
 'paypal-gateway', 'PayPal API rate limiting triggered.',
 'Request retry logic added. PayPal approved higher rate limit.',
 NOW() - INTERVAL 5 DAY, NOW() - INTERVAL 4 DAY),

('inc-014', 'cust-45837', 'SINC-014', 'payment_gateway', 'high', 'open',
 'Bulk payment batch rejected by processor',
 'Monthly bulk payment file rejected. 120 payment records need reprocessing.',
 'batch-payment-processor', NULL, NULL,
 NOW() - INTERVAL 4 HOUR, NOW() - INTERVAL 1 HOUR),

('inc-015', NULL, 'SINC-015', 'service_degradation', 'medium', 'resolved',
 'Database slow query alert — transactions table',
 'Slow queries detected on transactions table causing payment processing delays.',
 'mysql-primary', 'Missing index on customer_id + created_at composite.',
 'Added composite index. Query performance restored.',
 NOW() - INTERVAL 10 DAY, NOW() - INTERVAL 9 DAY),

('inc-016', NULL, 'SINC-016', 'network', 'medium', 'resolved',
 'CDN connectivity issues — payment page',
 'Payment checkout page experiencing slow load times due to CDN issues.',
 'cdn-edge', 'CDN provider routing issue.',
 'CDN failover activated. Page load times restored.',
 NOW() - INTERVAL 7 DAY, NOW() - INTERVAL 6 DAY),

('inc-017', 'cust-45839', 'SINC-017', 'security_breach', 'critical', 'investigating',
 'Unauthorized login from suspicious IP — CyberShield',
 'Enterprise account accessed from known Tor exit node IP. Possible compromise.',
 'auth-service', NULL, NULL,
 NOW() - INTERVAL 1 HOUR, NOW() - INTERVAL 20 MINUTE),

('inc-018', NULL, 'SINC-018', 'payment_gateway', 'high', 'mitigated',
 'Payment gateway certification renewal missed — Stripe',
 'TLS certificate on payment gateway relay expired. Short window of failed connections.',
 'stripe-payment-api', 'Certificate auto-renewal process failed.',
 'Certificate renewed manually. Auto-renewal process fixed.',
 NOW() - INTERVAL 14 DAY, NOW() - INTERVAL 13 DAY),

('inc-019', NULL, 'SINC-019', 'service_degradation', 'medium', 'resolved',
 'Fraud detection false positives — elevated rate',
 'Fraud detection model generating 5x normal rate of false positives.',
 'fraud-detection-service', 'Model retrained on biased dataset.',
 'Model rolled back to previous version. False positive rate normalized.',
 NOW() - INTERVAL 20 DAY, NOW() - INTERVAL 18 DAY),

('inc-020', NULL, 'SINC-020', 'payment_gateway', 'high', 'investigating',
 'Payment retry storm — cascading failures',
 'Excessive payment retries from multiple customers overwhelming the gateway during degradation window.',
 'stripe-payment-api', 'No exponential backoff on retry logic.',
 NULL,
 NOW() - INTERVAL 32 MINUTE, NOW() - INTERVAL 5 MINUTE);

-- =============================================================
-- SYSTEM EVENTS (50 records)
-- =============================================================
INSERT INTO system_events (event_id, service, event_type, severity, message, correlation_id, timestamp) VALUES
-- KEY EVENTS: Payment API gateway timeouts (correlate to INC-1042)
('evt-001', 'payment-api',      'timeout',      'high',     'Gateway timeout connecting to stripe-v2: connection timed out after 30s',           'corr-stripe-001', NOW() - INTERVAL 30 MINUTE),
('evt-002', 'payment-api',      'timeout',      'high',     'Gateway timeout connecting to stripe-v2: socket read timeout',                       'corr-stripe-001', NOW() - INTERVAL 28 MINUTE),
('evt-003', 'payment-api',      'timeout',      'high',     'Gateway timeout connecting to stripe-v2: upstream unreachable',                      'corr-stripe-001', NOW() - INTERVAL 25 MINUTE),
('evt-004', 'payment-api',      'error',        'high',     'HTTP 504 returned from stripe-v2 gateway endpoint: /v1/charges',                     'corr-stripe-001', NOW() - INTERVAL 22 MINUTE),
('evt-005', 'payment-api',      'error',        'high',     'HTTP 504 returned from stripe-v2 gateway endpoint: /v1/charges',                     'corr-stripe-001', NOW() - INTERVAL 20 MINUTE),
('evt-006', 'payment-api',      'error',        'critical', 'Circuit breaker OPEN: stripe-v2 failure rate exceeded 80% threshold',                'corr-stripe-001', NOW() - INTERVAL 18 MINUTE),
('evt-007', 'payment-api',      'degradation',  'high',     'Payment API P99 latency: 8240ms (SLA threshold: 2000ms)',                            'corr-stripe-001', NOW() - INTERVAL 15 MINUTE),
('evt-008', 'payment-api',      'degradation',  'high',     'Payment API P99 latency: 9100ms — SLA breach',                                       'corr-stripe-001', NOW() - INTERVAL 12 MINUTE),
('evt-009', 'stripe-connector', 'error',        'high',     'Stripe API response: {"error": {"type": "api_connection_error", "message": "timed out"}}', 'corr-stripe-001', NOW() - INTERVAL 29 MINUTE),
('evt-010', 'stripe-connector', 'error',        'high',     'Stripe webhook delivery failed: Unable to reach stripe-v2 endpoint',                 'corr-stripe-001', NOW() - INTERVAL 20 MINUTE),

-- Monitoring and alerting events
('evt-011', 'alertmanager',     'warning',      'medium',   'ALERT: PaymentAPILatencyHigh firing for 15 minutes',                                 NULL, NOW() - INTERVAL 15 MINUTE),
('evt-012', 'alertmanager',     'critical',     'critical', 'ALERT: PaymentGatewayCircuitBreakerOpen — immediate action required',                  NULL, NOW() - INTERVAL 18 MINUTE),
('evt-013', 'pagerduty',        'info',         'high',     'PagerDuty incident created: payment-api-degradation-2024',                            NULL, NOW() - INTERVAL 17 MINUTE),
('evt-014', 'health-checker',   'error',        'high',     'Health check FAILED: payment-api /health returned 503',                               NULL, NOW() - INTERVAL 20 MINUTE),
('evt-015', 'health-checker',   'warning',      'medium',   'Health check DEGRADED: payment-api /health responding slowly (4200ms)',               NULL, NOW() - INTERVAL 25 MINUTE),

-- Database events
('evt-016', 'mysql-primary',    'warning',      'medium',   'Slow query detected: SELECT * FROM transactions WHERE customer_id=? (2100ms)',        NULL, NOW() - INTERVAL 1 HOUR),
('evt-017', 'mysql-primary',    'info',         'low',      'Connection pool utilization at 78% — approaching threshold',                          NULL, NOW() - INTERVAL 45 MINUTE),
('evt-018', 'mysql-replica',    'info',         'low',      'Replication lag: 2.3 seconds (normal: < 1s)',                                         NULL, NOW() - INTERVAL 30 MINUTE),

-- Auth service events
('evt-019', 'auth-service',     'warning',      'medium',   'Failed login attempt from IP 185.220.101.45 (Tor exit node)',                         'corr-auth-001', NOW() - INTERVAL 1 HOUR),
('evt-020', 'auth-service',     'critical',     'critical', 'Multiple failed login attempts for enterprise account — rate limit triggered',         'corr-auth-001', NOW() - INTERVAL 55 MINUTE),

-- Fraud detection events
('evt-021', 'fraud-detection',  'warning',      'high',     'High-value transaction flagged: $4999.99 — risk score 0.92',                          'corr-fraud-001', NOW() - INTERVAL 6 HOUR),
('evt-022', 'fraud-detection',  'info',         'medium',   'Fraud detection model prediction: SUSPICIOUS — transaction held for review',           'corr-fraud-001', NOW() - INTERVAL 6 HOUR),

-- Webhook service events
('evt-023', 'webhook-service',  'warning',      'medium',   'Webhook delivery queue depth: 1240 (normal: < 100)',                                  NULL, NOW() - INTERVAL 2 HOUR),
('evt-024', 'webhook-service',  'error',        'medium',   'Webhook delivery failed for endpoint customer-45821.techcorp.io: connection refused', NULL, NOW() - INTERVAL 25 MINUTE),
('evt-025', 'webhook-service',  'info',         'low',      'Webhook retry scheduled for failed delivery: attempt 2 of 5',                         NULL, NOW() - INTERVAL 20 MINUTE),

-- Load balancer events
('evt-026', 'nginx-lb',         'warning',      'medium',   'Upstream payment-api health check failing: removing from pool',                       'corr-stripe-001', NOW() - INTERVAL 19 MINUTE),
('evt-027', 'nginx-lb',         'info',         'medium',   'Traffic failover activated: routing to backup payment-api-02',                        'corr-stripe-001', NOW() - INTERVAL 18 MINUTE),

-- Billing service events
('evt-028', 'billing-service',  'warning',      'medium',   'Subscription renewal failure: customer cust-45831 — card declined',                  NULL, NOW() - INTERVAL 1 DAY),
('evt-029', 'billing-service',  'info',         'low',      'Retry schedule created for failed renewal: attempt 1 in 24h',                        NULL, NOW() - INTERVAL 1 DAY),
('evt-030', 'billing-service',  'warning',      'medium',   'Dunning process initiated for 3 accounts with failed payments',                       NULL, NOW() - INTERVAL 2 DAY),

-- General payment events
('evt-031', 'payment-api',      'info',         'low',      'Payment transaction initiated: customer cust-45821, amount $1299.00',                 'corr-stripe-001', NOW() - INTERVAL 29 MINUTE),
('evt-032', 'payment-api',      'error',        'high',     'Payment transaction failed: PAYMENT_GATEWAY_TIMEOUT for customer cust-45821',         'corr-stripe-001', NOW() - INTERVAL 28 MINUTE),
('evt-033', 'payment-api',      'error',        'high',     'Payment transaction failed: PAYMENT_GATEWAY_TIMEOUT for customer cust-45821 (retry 1)', 'corr-stripe-001', NOW() - INTERVAL 25 MINUTE),
('evt-034', 'payment-api',      'error',        'high',     'Payment transaction failed: PAYMENT_GATEWAY_TIMEOUT for customer cust-45821 (retry 2)', 'corr-stripe-001', NOW() - INTERVAL 20 MINUTE),
('evt-035', 'payment-api',      'error',        'high',     'Payment transaction failed: PAYMENT_GATEWAY_TIMEOUT for customer cust-45821 (retry 3)', 'corr-stripe-001', NOW() - INTERVAL 15 MINUTE),
('evt-036', 'payment-api',      'error',        'high',     'Payment transaction failed: PAYMENT_GATEWAY_TIMEOUT for customer cust-45821 (retry 4)', 'corr-stripe-001', NOW() - INTERVAL 10 MINUTE),

-- Cache events
('evt-037', 'redis-cache',      'warning',      'medium',   'Cache hit rate dropped to 42% (normal: > 80%) — possible cache invalidation storm',  NULL, NOW() - INTERVAL 20 MINUTE),
('evt-038', 'redis-cache',      'info',         'low',      'Cache eviction rate elevated: 2400 keys/min',                                         NULL, NOW() - INTERVAL 15 MINUTE),

-- SDK events
('evt-039', 'payment-sdk',      'error',        'high',     'SDK v4.2 authentication error: invalid signature on payment request',                  NULL, NOW() - INTERVAL 12 HOUR),
('evt-040', 'payment-sdk',      'error',        'high',     'SDK v4.2 authentication error: timestamp drift detected',                              NULL, NOW() - INTERVAL 11 HOUR),

-- Older resolved events for context
('evt-041', 'payment-api',      'info',         'low',      'Payment gateway stripe-v2 healthy: latency 145ms',                                    NULL, NOW() - INTERVAL 3 HOUR),
('evt-042', 'payment-api',      'info',         'low',      'Payment gateway stripe-v2 healthy: latency 132ms',                                    NULL, NOW() - INTERVAL 4 HOUR),
('evt-043', 'payment-api',      'info',         'low',      'Payment gateway stripe-v2 healthy: latency 158ms',                                    NULL, NOW() - INTERVAL 5 HOUR),
('evt-044', 'payment-api',      'info',         'low',      'Daily payment volume report: 2,841 transactions processed, 99.2% success rate',       NULL, NOW() - INTERVAL 1 DAY),
('evt-045', 'stripe-connector', 'info',         'low',      'Stripe API connection pool healthy: 0 errors in last 1h',                             NULL, NOW() - INTERVAL 3 HOUR),
('evt-046', 'billing-service',  'info',         'low',      'Monthly billing cycle completed: 1,240 renewals processed',                           NULL, NOW() - INTERVAL 5 DAY),
('evt-047', 'audit-service',    'info',         'low',      'Audit log rotation completed: archived 90-day records',                               NULL, NOW() - INTERVAL 7 DAY),
('evt-048', 'ops-agent',        'info',         'low',      'Agent health check passed: all tools operational',                                    NULL, NOW() - INTERVAL 2 HOUR),
('evt-049', 'payment-api',      'warning',      'medium',   'Stripe rate limit approaching: 85% of hourly limit consumed',                         'corr-stripe-001', NOW() - INTERVAL 10 MINUTE),
('evt-050', 'ops-agent',        'warning',      'high',     'Pattern detected: 5 PAYMENT_GATEWAY_TIMEOUT failures from same customer in 30min',    'corr-stripe-001', NOW() - INTERVAL 8 MINUTE);
