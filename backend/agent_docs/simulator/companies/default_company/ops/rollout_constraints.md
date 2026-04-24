# Rollout Constraints (Mock)

Synthetic operational constraints for simulator testing.

## Commerce / Systems

- Price table updates can be deployed daily, but:
  - tax/marketplace sync can lag by up to 24 hours.
- Discount rule conflicts increase support tickets by ~18% after major repricing.

## Retail Partner Contracts

- 14-day notice required for MSRP changes above 7%.
- 22% of partner stores limit mid-season price changes.

## Support Capacity

- Pricing complaints above baseline +30% causes SLA breaches in week 1.

## Practical Recommendation

- Prefer phased rollout by channel:
  - week 1: DTC test cohorts
  - week 3: selected retail partners
  - week 5: broader expansion if KPI gates pass.
