# Governance Workbook Structure

APOLLO stores governance data in an Excel workbook at `data/input/PKD Governance Data.xlsx`. If the file does not exist when data is recorded, APOLLO creates it with four default sheets: Referenda, Proposals, Context, and ExecutionResults.

## Default Sheets

- **Referenda** – snapshots of referendum metadata pulled from the chain for audit and analysis.
- **Proposals** – generated proposal texts along with optional submission identifiers.
- **Context** – structured context blobs captured for traceability.
- **ExecutionResults** – details about on-chain execution attempts, such as status, block hash, and outcome.

Additional sheets may be added by future features, but these are the core ones currently used.
