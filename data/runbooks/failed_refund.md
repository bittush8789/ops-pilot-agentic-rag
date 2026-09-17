# Failed Refund Investigation Runbook

**Document ID:** RB-PAY-004  
**Version:** 1.5  
**Owner:** Payment Operations Team  
**Last Updated:** 2024-01-12  
**Classification:** Internal Operations  

---

## Overview

This runbook provides procedures for investigating and resolving failed or delayed refunds.

---

## Refund Failure Scenarios

| Scenario | Symptoms | Resolution |
|----------|----------|------------|
| Refund initiated but not received | Transaction in `refunded` status but customer reports no credit | Check gateway refund processing time, escalate to gateway support |
| Refund processing failed | Transaction stuck in `pending` status | Re-initiate refund via gateway console |
| Refund on expired card | Customer closed/expired card after purchase | Coordinate alternative refund method |
| Bank transfer refund delayed | ACH/wire refund exceeding normal timeline | Contact banking partner |
| Partial refund disputed | Customer claims wrong amount refunded | Review original transaction and refund amounts |

---

## Investigation Steps

### Step 1: Verify Refund Initiation

1. Confirm the original transaction ID and amount
2. Check that a refund transaction exists in our system
3. Verify the `status` field on the refund transaction
4. Confirm the gateway reference ID for the refund

### Step 2: Check Gateway Status

1. Log into the payment gateway console (Stripe Dashboard / PayPal)
2. Search for the refund using the `reference_id`
3. Check refund status on the gateway side
4. Note the expected clearing date from the gateway

### Step 3: SLA Check

Standard refund timelines:

| Payment Method | Expected Timeline | Escalation Trigger |
|----------------|-------------------|--------------------|
| Credit card | 5–10 business days | > 10 days |
| Debit card | 2–5 business days | > 7 days |
| Bank transfer / ACH | 3–7 business days | > 10 days |
| PayPal | 3–5 business days | > 7 days |

### Step 4: Resolution Actions

- **Within SLA:** Inform customer of expected timeline, add ticket note
- **Outside SLA:** Escalate to gateway support with transaction and refund reference IDs
- **Card closed:** Coordinate with customer for alternative (bank transfer or check)
- **Gateway error:** Re-initiate refund after resolving gateway issue

---

## Do NOT Do

- ❌ Do NOT initiate a duplicate refund without confirming the first refund failed
- ❌ Do NOT issue refunds beyond your authorization level without approval

---

## Escalation

Contact gateway support after SLA breach:
- Stripe: https://support.stripe.com
- PayPal: Merchant support hotline

---

## Related Runbooks

- `duplicate_payment.md` — Duplicate charge investigation
- `payment_failure.md` — General payment issues
