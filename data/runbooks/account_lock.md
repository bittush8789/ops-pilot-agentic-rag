# Account Lock and Suspension Runbook

**Document ID:** RB-ACC-001  
**Version:** 2.2  
**Owner:** Account Operations Team  
**Last Updated:** 2024-01-18  
**Classification:** Internal Operations  

---

## Overview

This runbook covers account lock and suspension scenarios including automatic suspension due to failed payments, security-initiated locks, and the account reactivation process.

---

## Account Status Definitions

| Status | Meaning | Customer Impact |
|--------|---------|-----------------|
| `active` | Account in good standing | Full service access |
| `suspended` | Temporarily disabled | No payment processing, read-only access |
| `closed` | Permanently closed | No access |
| `pending` | Awaiting verification | Limited access |

---

## Common Suspension Causes

### 1. Payment Failure Threshold (Automatic)

- 3 or more failed payment attempts within 30 days
- Dunning process exhausted without payment
- Subscription renewal failed after maximum retries

**Resolution:** Customer must update payment method and settle outstanding balance. Manual reactivation by Operations Engineer.

### 2. Fraud Suspected (Security-Initiated)

- Fraud detection score exceeds 0.85 threshold
- Login from suspicious IP (Tor exit nodes, known fraud IPs)
- Unusual transaction patterns

**Resolution:** Security team review required. Do NOT reactivate without security team clearance.

### 3. Compliance / Regulatory Hold

- AML screening hit
- Sanctions list match
- Regulatory investigation request

**Resolution:** Escalate to Compliance team immediately. Do NOT attempt to resolve without compliance guidance.

### 4. Manual Admin Suspension

- Chargeback threshold exceeded
- Terms of service violation

**Resolution:** Review reason for manual suspension. Escalate to account manager if disputed.

---

## Investigation Steps

### For Payment-Related Suspension

1. Verify the account status in the customers table
2. Review failed transactions — count, amount, failure reasons
3. Check incidents related to the customer
4. Confirm dunning emails were sent
5. Review customer communication history in tickets

### For Security-Related Lock

1. Check system events for security alerts linked to the customer
2. Review login events (unusual IP, geolocation changes)
3. Check for suspicious transaction patterns
4. Contact the customer through verified contact information

---

## Reactivation Procedure

### Payment-Related Suspension Reactivation

**Pre-conditions:**
- [ ] Customer has updated their payment method
- [ ] Outstanding balance is settled or payment plan agreed
- [ ] No open fraud flags on the account

**Steps:**
1. Verify payment method update in billing system
2. Process outstanding payment
3. Update account status to `active`
4. Add note to customer ticket documenting reason for reactivation
5. Send reactivation confirmation to customer

**Authorization Required:**
- Balance < $500: Operations Engineer
- Balance $500–$5,000: Senior Operations Engineer
- Balance > $5,000: Operations Manager

### Security-Related Suspension Reactivation

- **Requires Security Team sign-off before any reactivation action**
- Do NOT reactivate without written approval from Security Lead
- Document all steps taken and approvals received

---

## Do NOT Do

- ❌ Do NOT reactivate accounts flagged for fraud without security clearance
- ❌ Do NOT manually override compliance holds
- ❌ Do NOT reactivate without verifying payment is resolved

---

## Related Runbooks

- `payment_failure.md` — Payment failure that led to suspension
- `incident_escalation.md` — Escalation procedures
