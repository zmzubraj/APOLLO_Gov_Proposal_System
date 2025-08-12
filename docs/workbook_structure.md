# Governance Workbook Structure

APOLLO stores governance data in an Excel workbook at `data/input/PKD Governance Data.xlsx`. If the file does not exist when data is recorded, APOLLO creates it with four default sheets: Referenda, Proposals, Context, and ExecutionResults.

## Default Sheets

- **Referenda** – snapshots of referendum metadata pulled from the chain for audit and analysis.
- **Proposals** – generated proposal texts along with optional submission identifiers.
- **Context** – structured context blobs captured for traceability.
- **ExecutionResults** – details about on-chain execution attempts, such as status, block hash, and outcome.

Additional sheets may be added by future features, but these are the core ones currently used.

## Column Reference

### Referenda

| Column | Description |
| --- | --- |
| Referendum_ID | Unique index of the referendum. |
| Title | Title of the referendum as posted on-chain. |
| Content | Text body or summary describing the referendum. |
| Start | Timestamp when voting began. |
| End | Timestamp when voting closed. |
| Duration_days | Length of the voting period in days. |
| Participants | Number of accounts that cast a vote. |
| ayes_amount | Total voting weight of ayes. |
| nays_amount | Total voting weight of nays. |
| Total_Voted_DOT | Sum of DOT used in the vote. |
| Eligible_DOT | Total DOT eligible to participate. |
| Not_Perticipated_DOT | DOT that did not participate. |
| Voted_percentage | Percentage of eligible DOT that voted. |
| Status | Current lifecycle state of the referendum. |

### Proposals

| Column | Description |
| --- | --- |
| timestamp | When the proposal text was generated. |
| proposal_text | The generated proposal content. |
| submission_id | Optional on-chain submission identifier. |

### Context

| Column | Description |
| --- | --- |
| timestamp | When the context data was recorded. |
| context_json | JSON-encoded context blob for auditing. |

### ExecutionResults

| Column | Description |
| --- | --- |
| timestamp | Time the execution attempt was logged. |
| submission_id | Related submission identifier, if any. |
| status | Resulting status of the execution attempt. |
| block_hash | Block hash of the attempted execution. |
| outcome | Textual outcome message. |
| extrinsic_hash | Extrinsic hash associated with the execution. |
