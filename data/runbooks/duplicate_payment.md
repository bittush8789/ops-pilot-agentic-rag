# Duplicate Payment Runbook

**Document ID:** RB-PAY-003  
**Version:** 1.8  
**Owner:** Payment Operations Team  
**Last Updated:** 2024-01-10  
**Classification:** Internal Operations  

---

## Overview

This runbook covers the identification, investigation, and resolution of duplicate payment transactions. Duplicate payments occur when a customer is charged more than once for the same transaction.

---

## Identifying Duplicate Payments

A duplicate payment is confirmed when:

- Two or more transactions have the **same customer, amount, and payment method**
- Transactions occurred within a **short time window** (< 5 minutes apart)
- The `failure_reason` field shows `DUPLICATE_TRANSACTION` on one of the records
- The customer reports seeing multiple charges on their statement

### Duplicate Payment Query

```sql
SELECT customer_id, amount, payment_method, COUNT(*) as count,
       MIN(created_at) as first_charge, MAX(created_at) as last_charge
FROM transactions
WHERE status IN ('success', 'pending')
AND created_at >= NOW() - INTERVAL 24 HOUR
GROUP BY customer_id, amount, payment_method, DATE(created_at)
HAVING COUNT(*) > 1;
```

---

## Investigation Steps

1. **Confirm the duplicate** — verify transaction IDs, amounts, and timestamps
2. **Identify the source** — was it a customer double-click, retry logic, or system bug?
3. **Check webhook events** — did the webhook fire multiple times?
4. **Review idempotency keys** — were idempotency keys used correctly?
5. **Check if any transaction is already in `refunded` status** — if so, refund may already be in progress

---

## Resolution Actions

### Customer-Side Duplicate (Double Submit)

1. Add a note to the ticket explaining the duplicate
2. Initiate a refund for the duplicate transaction amount
3. Notify the customer that the duplicate charge will be refunded within 5–7 business days

### System-Side Duplicate (Bug or Missing Idempotency)

1. Create a bug ticket for the engineering team
2. Refund all duplicate charges
3. Audit similar transactions in the last 7 days for other affected customers
4. Engineering must implement idempotency keys before closing the bug

---

## Refund Authorization Levels

| Amount | Authorization Required |
|--------|------------------------|
| < $100 | Operations Engineer |
| $100–$1,000 | Senior Operations Engineer |
| > $1,000 | Operations Manager |

---

## Related Runbooks

- `failed_refund.md` — If the refund itself fails
- `payment_failure.md` — General payment investigation
