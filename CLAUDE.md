# Webmaster ERP

## Project Overview

| Key | Value |
|---|---|
| Project Name | Webmaster ERP |
| Company | Webmaster Consultancy Pte Ltd |
| Country | Singapore |
| Currency | SGD |
| Timezone | Asia/Singapore |
| Database | PostgreSQL |

## Purpose

Develop a custom ERP / business management system to eventually replace Odoo.

This is a greenfield project. No application code, database schema, or
business workflow assumptions exist yet. Documentation and rules are being
established first; detailed requirements and architecture will be developed
before any application coding begins.

## Initial Business Areas

These are the initial candidate business areas for the ERP. None of these
have detailed requirements yet — they are listed here only to scope the
eventual project.

- CRM
- Sales
- Customer Management
- Service Contracts
- Helpdesk
- Service Operations
- Projects
- Timesheets
- Billing
- Accounts Receivable
- Accounts Payable
- Purchasing
- Inventory
- Hardware Management
- Commission Management
- Management Reporting
- AI Assistant

## Development Rules

- Use a modular and maintainable architecture.
- Use PostgreSQL as the primary database.
- All important financial and operational transactions must have audit trails.
- Never permanently delete important business or financial records.
- Use soft-delete or archival where appropriate.
- Database changes must use migrations.
- Never modify production data directly.
- Authentication and role-based permissions are required.
- Validate data on both frontend and backend.
- Write automated tests for important business logic.
- Do not introduce unnecessary dependencies.
- Keep business logic separate from the user interface.
- Document major architectural decisions.
- Do not change the approved architecture without explaining the reason first.
- Never assume a business rule when requirements have not been provided.

## Documentation

- [docs/business-requirements.md](docs/business-requirements.md) — business requirements (placeholder, to be developed)
- [docs/system-architecture.md](docs/system-architecture.md) — system architecture (placeholder, to be developed)

## Status

This project is in the documentation/planning stage. No application code has
been written yet.
