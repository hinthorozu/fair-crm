# FAIR CRM Product Vision

## Purpose

FAIR CRM is a product for managing fair and exhibition relationships.

It helps manage customers, contacts, fairs, fair participations, stand information, imported exhibitor data, scraper outputs, duplicate detection, and CRM follow-up workflows.

## Target Users

Potential users include:

- Fair sales teams
- Exhibition organizers
- Stand and event service providers
- CRM operators
- Data import operators
- Management teams that need reporting

## Core Problem

Fair data is usually fragmented across Excel files, scraped exhibitor lists, manual notes, contact records, and repeated company names.

The product must make it easy to:

- Import exhibitor/customer data
- Detect duplicates
- Merge incomplete records safely
- Track customers across multiple fairs
- Manage contacts and communication details
- Prepare reports and follow-up lists

## Product Principles

1. Do not blindly import duplicate records.
2. Always preview imported data before writing final CRM records.
3. Normalize customer names for matching, but preserve original display names.
4. Keep platform concerns in KYROX Core.
5. Keep product language user-facing Turkish, while backend/API/database remain English.
6. Prefer clear workflows over hidden automation.

## First Product Slice

The first slice is Customer.

Customer is the main CRM account aggregate. It represents an organization or business entity that may participate in fairs, receive offers, appear in imports, or be contacted by the sales team.
