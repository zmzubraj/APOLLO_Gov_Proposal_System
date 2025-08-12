# Governance Workbook Structure

APOLLO stores governance data in an Excel workbook at `data/input/PKD Governance Data.xlsx`. The file is created automatically if it does not exist when data is recorded.

## Default Sheets

- **Referenda** – snapshots of referendum metadata pulled from the chain for audit and analysis.
- **Proposals** – generated proposal texts along with optional submission identifiers.
- **ExecutionResults** – details about on-chain execution attempts, such as status, block hash, and outcome.

## Optional Sheets

- **Context** – structured context blobs captured for traceability; this sheet appears only when context is recorded.

Additional sheets may be added by future features, but these are the core ones currently used.
