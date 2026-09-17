# Payment Gateway Timeout Runbook

**Document ID:** RB-PAY-001  
**Version:** 2.4  
**Owner:** Payment Operations Team  
**Last Updated:** 2024-01-15  
**Classification:** Internal Operations  

---

## Overview

This runbook covers the investigation and resolution procedure for payment gateway timeout incidents. Gateway timeouts occur when the payment processing service cannot establish or maintain a connection with the upstream payment provider (Stripe, PayPal, etc.) within the acceptable time window.

---

## Symptoms

- Multiple consecutive payment failures with error code `PAYMENT_GATEWAY_TIMEOUT`
- Payment API P99 latency exceeding 2,000ms (normal baseline: 150–250ms)
- HTTP 504 Gateway Timeout errors from the payment endpoint
- Circuit breaker transitioning to OPEN state
- Health check failures on the payment-api service
- Customers reporting checkout failures or payment page not loading
- Increased support ticket volume related to payment failures
- Alert: `PaymentGatewayCircuitBreakerOpen` firing in alertmanager

---

## Business Impact Assessment

| Severity | Trigger Condition | Typical Impact |
|----------|-------------------|----------------|
| LOW | < 5 timeouts/hour, isolated customer | Single customer affected, no revenue impact |
| MEDIUM | 5–20 timeouts/hour or < 3 customers | Multiple customers affected, revenue at risk |
| HIGH | > 20 timeouts/hour or > 3 customers | Broad customer impact, significant revenue loss |
| CRITICAL | Gateway circuit breaker OPEN | All new payments blocked, immediate escalation required |

---

## Pre-Investigation Checklist

Before beginning investigation, confirm:

- [ ] Check Stripe Status Page: https://status.stripe.com
- [ ] Check PayPal Status Page: https://www.paypal-status.com
- [ ] Review alertmanager for active payment alerts
- [ ] Identify scope: Is this one customer or multiple customers?
- [ ] Check if a recent deployment occurred in the last 2 hours

---

## Investigation Steps

### Step 1: Assess Transaction Failure Pattern

1. Query failed transactions for the affected customer(s) in the last 60 minutes
2. Note the `failure_reason` field — confirm it is `PAYMENT_GATEWAY_TIMEOUT`
3. Count total failures vs. successful transactions
4. Determine if failures are recurring retries of the same amount (retry storm indicator)
5. Check `gateway` field to identify which gateway is failing (stripe-v2, paypal, plaid)

**Key Query:**
```sql
SELECT customer_id, COUNT(*) as failures, failure_reason, gateway, MIN(created_at), MAX(created_at)
FROM transactions
WHERE status = 'failed' AND failure_reason = 'PAYMENT_GATEWAY_TIMEOUT'
AND created_at >= NOW() - INTERVAL 1 HOUR
GROUP BY customer_id, failure_reason, gateway;
```

### Step 2: Check System Events

1. Filter system events for the `payment-api` and `stripe-connector` services in the last 60 minutes
2. Look for timeout messages, HTTP 504 errors, circuit breaker events
3. Check the `correlation_id` field to group related events
4. Look for `PaymentAPILatencyHigh` and `PaymentGatewayCircuitBreakerOpen` alerts
5. Review `nginx-lb` events for upstream failover activation

### Step 3: Determine Blast Radius

1. Query all customers with `PAYMENT_GATEWAY_TIMEOUT` failures in the last 60 minutes
2. If > 1 customer affected, this is likely a systemic gateway issue, not customer-specific
3. Check if affected customers share the same gateway (e.g., all using stripe-v2)
4. Review any existing open incidents related to payment-gateway category

### Step 4: Check Existing Incidents

1. Search for open incidents with `category = payment_gateway` and `status IN (open, investigating)`
2. If a matching incident already exists, do not create a duplicate — add a note to the existing incident
3. If no incident exists and this is a systemic issue, proceed to create one

### Step 5: Review Payment API Metrics

1. Review P99 latency events from system_events for payment-api
2. Check circuit breaker status events
3. Review if Stripe rate limiting events are present (approaching hourly limit)
4. Check for DNS resolution events or TLS certificate errors

---

## Recommended Actions

### Action Matrix

| Scope | Duration | Recommended Action |
|-------|----------|--------------------|
| Single customer, < 5 failures | < 15 min | Add ticket note, monitor for recurrence |
| Single customer, 5+ failures | > 15 min | Create HIGH-priority incident, notify customer |
| Multiple customers | Any | Create CRITICAL incident, escalate to on-call |
| Circuit breaker OPEN | Any | Immediate escalation to payment engineering team |
| Suspected retry storm | Any | Throttle retries, notify affected customers |

### For Single-Customer Timeout Pattern

1. **Create a HIGH-priority payment_gateway incident** linked to the customer
2. **Update the ticket status** to `investigating`
3. **Add a detailed ticket note** with:
   - Number of failed transactions and timestamps
   - Specific failure_reason and gateway
   - Related system event correlation IDs
   - Current status of the gateway per status page
4. **Advise the customer** to wait 15–30 minutes before retrying
5. **Avoid encouraging repeated retries** — this contributes to retry storms

### For Multi-Customer / Systemic Issue

1. **Create a CRITICAL-severity incident** (not customer-specific)
2. **Activate the incident communication plan** — notify payment operations on-call
3. **Engage the gateway vendor** (Stripe/PayPal support) with correlation IDs
4. **Post a status page update** for affected customers
5. **Monitor circuit breaker state** — wait for it to CLOSE before clearing

---

## Escalation Path

```
Level 1: Operations Engineer (this runbook)
   ↓ (if unresolved after 15 min)
Level 2: Payment Operations On-Call
   ↓ (if systemic / circuit breaker open)
Level 3: Payment Engineering Lead
   ↓ (if gateway vendor issue confirmed)
Level 4: Stripe/PayPal Account Manager + Engineering
```

**On-Call Contact:**  
Payment Ops: ops-oncall@company.internal  
PagerDuty Service: `payment-operations`

---

## Do NOT Do

- ❌ Do NOT manually retry payments in bulk without throttling
- ❌ Do NOT create duplicate incidents if one already exists
- ❌ Do NOT restart the payment-api service without engineering approval
- ❌ Do NOT modify gateway configuration without a change request
- ❌ Do NOT advise customers to retry repeatedly (retry storm risk)

---

## Resolution Criteria

The incident can be marked **resolved** when:

- [ ] Payment API P99 latency returns to < 300ms for 10+ consecutive minutes
- [ ] Circuit breaker returns to CLOSED state
- [ ] Zero `PAYMENT_GATEWAY_TIMEOUT` failures in the last 15 minutes
- [ ] Stripe/PayPal status page shows all systems operational
- [ ] Health checks for payment-api passing consistently

---

## Post-Incident Actions

1. Document root cause in incident record
2. Calculate total failed transactions and revenue impact
3. Create follow-up ticket for retry logic improvement (exponential backoff)
4. Schedule post-mortem if duration > 30 minutes or > 10 customers affected
5. Review circuit breaker thresholds if appropriate

---

## Related Runbooks

- `payment_failure.md` — General payment failure investigation
- `incident_escalation.md` — Escalation procedures
- `account_lock.md` — Account suspension due to payment failures
