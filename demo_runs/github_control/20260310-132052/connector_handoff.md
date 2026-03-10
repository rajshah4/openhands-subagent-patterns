# Connector Handoff

Blocked work to resume once the salesforce connector is available:
- CRM contact sync
- opportunity writeback
- connector-backed smoke tests

App work that can continue independently:
- dashboard and navigation shell
- approval workflow screens
- lead intake forms
- user and role model

Integration notes:
- wire the connector behind the contract documented in `connector_plan.md`
- validate smoke tests before merging the connector branch into the app flow
