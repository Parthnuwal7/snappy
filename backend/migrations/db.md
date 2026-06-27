## Table `users`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `supabase_id` | `uuid` |  Nullable Unique |
| `email` | `varchar` |  Unique |
| `password_hash` | `varchar` |  Nullable |
| `is_active` | `bool` |  Nullable |
| `is_onboarded` | `bool` |  Nullable |
| `device_id` | `text` |  Nullable |
| `device_info` | `jsonb` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `last_login` | `timestamp` |  Nullable |
| `firm_id` | `int4` |  Nullable |
| `role_id` | `int4` |  Nullable |

## Table `firm_details`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `user_id` | `int4` |  Unique |
| `firm_name` | `varchar` |  |
| `firm_address` | `text` |  |
| `firm_email` | `varchar` |  Nullable |
| `firm_phone` | `varchar` |  Nullable |
| `firm_phone_2` | `varchar` |  Nullable |
| `firm_website` | `varchar` |  Nullable |
| `logo_path` | `text` |  Nullable |
| `signature_path` | `text` |  Nullable |
| `terms_and_conditions` | `text` |  Nullable |
| `billing_terms` | `text` |  Nullable |
| `default_template` | `varchar` |  Nullable |
| `invoice_prefix` | `varchar` |  Nullable |
| `default_tax_rate` | `numeric` |  Nullable |
| `currency` | `varchar` |  Nullable |
| `show_due_date` | `bool` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `use_invoice_prefix` | `bool` |  Nullable |
| `email_subject_template` | `text` |  Nullable |
| `email_body_template` | `text` |  Nullable |
| `whatsapp_template` | `text` |  Nullable |
| `firm_id` | `int4` |  Nullable |

## Table `bank_accounts`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `user_id` | `int4` |  |
| `bank_name` | `varchar` |  Nullable |
| `account_number` | `varchar` |  Nullable |
| `account_holder_name` | `varchar` |  Nullable |
| `ifsc_code` | `varchar` |  Nullable |
| `upi_id` | `varchar` |  Nullable |
| `upi_qr_path` | `text` |  Nullable |
| `is_default` | `bool` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `firm_id` | `int4` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |

## Table `clients`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `created_by_user_id` | `int4` |  |
| `name` | `varchar` |  |
| `email` | `varchar` |  Nullable |
| `phone` | `varchar` |  Nullable |
| `address` | `text` |  Nullable |
| `tax_id` | `varchar` |  Nullable |
| `default_tax_rate` | `numeric` |  Nullable |
| `notes` | `text` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `firm_id` | `int4` |  Nullable |

## Table `items`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `created_by_user_id` | `int4` |  |
| `name` | `varchar` |  |
| `alias` | `varchar` |  Nullable |
| `description` | `text` |  Nullable |
| `default_rate` | `numeric` |  Nullable |
| `unit` | `varchar` |  Nullable |
| `hsn_code` | `varchar` |  Nullable |
| `is_active` | `bool` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `firm_id` | `int4` |  Nullable |

## Table `invoices`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `created_by_user_id` | `int4` |  |
| `client_id` | `int4` |  |
| `invoice_number` | `varchar` |  |
| `invoice_date` | `date` |  |
| `due_date` | `date` |  Nullable |
| `short_desc` | `text` |  Nullable |
| `subtotal` | `numeric` |  Nullable |
| `tax_rate` | `numeric` |  Nullable |
| `tax_amount` | `numeric` |  Nullable |
| `total` | `numeric` |  Nullable |
| `status` | `varchar` |  Nullable |
| `paid_date` | `date` |  Nullable |
| `notes` | `text` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `source` | `varchar` |  Nullable |
| `sent_at` | `timestamp` |  Nullable |
| `sent_channel` | `varchar` |  Nullable |
| `firm_id` | `int4` |  Nullable |
| `case_file_id` | `int4` |  Nullable |

## Table `invoice_items`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `invoice_id` | `int4` |  |
| `description` | `text` |  |
| `quantity` | `numeric` |  Nullable |
| `rate` | `numeric` |  Nullable |
| `amount` | `numeric` |  Nullable |

## Table `keepalive`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int8` | Primary |
| `pinged_at` | `timestamp` |  |
| `source` | `varchar` |  Nullable |

## Table `recurring_schedules`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `created_by_user_id` | `int4` |  |
| `client_id` | `int4` |  |
| `title` | `varchar` |  Nullable |
| `items` | `jsonb` |  |
| `tax_rate` | `numeric` |  Nullable |
| `short_desc` | `text` |  Nullable |
| `notes` | `text` |  Nullable |
| `frequency` | `varchar` |  |
| `start_date` | `date` |  |
| `next_run_date` | `date` |  |
| `end_date` | `date` |  Nullable |
| `last_run_date` | `date` |  Nullable |
| `active` | `bool` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `firm_id` | `int4` |  Nullable |

## Table `legal_feed_sources`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `name` | `varchar` |  |
| `content_type` | `varchar` |  |
| `court` | `varchar` |  Nullable |
| `kind` | `varchar` |  |
| `feed_url` | `varchar` |  Unique |
| `enabled` | `bool` |  |
| `weight` | `int4` |  |
| `created_at` | `timestamp` |  Nullable |

## Table `legal_feed_runs`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `started_at` | `timestamp` |  Nullable |
| `finished_at` | `timestamp` |  Nullable |
| `trigger` | `varchar` |  |
| `status` | `varchar` |  |
| `total_ingested` | `int4` |  |
| `results` | `json` |  Nullable |
| `enriched` | `int4` |  Nullable |
| `enrich_failed` | `int4` |  Nullable |

## Table `legal_feed_settings`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `ordering_mode` | `varchar` |  |

## Table `legal_feed_items`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `source_id` | `int4` |  Nullable |
| `content_type` | `varchar` |  |
| `title` | `text` |  |
| `summary` | `text` |  Nullable |
| `source_url` | `varchar` |  |
| `source_name` | `varchar` |  |
| `court` | `varchar` |  Nullable |
| `published_at` | `timestamp` |  Nullable |
| `ingested_at` | `timestamp` |  Nullable |
| `hidden` | `bool` |  |
| `dedup_key` | `varchar` |  |
| `headline` | `text` |  Nullable |
| `tldr` | `text` |  Nullable |
| `topics` | `json` |  Nullable |
| `importance` | `int4` |  Nullable |
| `image_url` | `varchar` |  Nullable |
| `embedding` | `json` |  Nullable |
| `embed_model` | `varchar` |  Nullable |
| `enriched_at` | `timestamp` |  Nullable |

## Table `legal_feed_preferences`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `user_id` | `int4` |  |
| `topic_weights` | `json` |  Nullable |
| `courts` | `json` |  Nullable |
| `interest_phrases` | `json` |  Nullable |
| `interest_embedding` | `json` |  Nullable |
| `embed_model` | `varchar` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `behavior_embedding` | `json` |  Nullable |
| `behavior_updated_at` | `timestamp` |  Nullable |

## Table `legal_feed_events`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `user_id` | `int4` |  |
| `item_id` | `int4` |  Nullable |
| `kind` | `varchar` |  |
| `created_at` | `timestamp` |  Nullable |

## Table `firms`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `name` | `varchar` |  |
| `created_at` | `timestamp` |  Nullable |

## Table `roles`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  |
| `name` | `varchar` |  |
| `description` | `text` |  Nullable |
| `permissions` | `json` |  Nullable |
| `is_system` | `bool` |  |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |

## Table `firm_invites`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  |
| `email` | `varchar` |  |
| `role_id` | `int4` |  |
| `token` | `varchar` |  |
| `status` | `varchar` |  |
| `invited_by` | `int4` |  Nullable |
| `expires_at` | `timestamp` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `accepted_at` | `timestamp` |  Nullable |

## Table `case_files`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |
| `case_number` | `varchar` |  |
| `title` | `varchar` |  |
| `client_id` | `int4` |  |
| `matter_type` | `varchar` |  Nullable |
| `court` | `varchar` |  Nullable |
| `court_case_number` | `varchar` |  Nullable |
| `stage` | `varchar` |  |
| `position` | `int4` |  |
| `handling_advocate_user_id` | `int4` |  Nullable |
| `next_hearing_date` | `date` |  Nullable |
| `open_date` | `date` |  Nullable |
| `description` | `text` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `jurisdiction` | `varchar` |  Nullable |
| `act_section` | `varchar` |  Nullable |
| `opposing_counsel` | `varchar` |  Nullable |
| `priority` | `varchar` |  |
| `filing_date` | `date` |  Nullable |
| `agreed_fee` | `numeric` |  Nullable |
| `lead_id` | `int4` |  Nullable |

## Table `case_parties`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `case_file_id` | `int4` |  Nullable |
| `name` | `varchar` |  |
| `role` | `varchar` |  Nullable |
| `created_at` | `timestamp` |  Nullable |

## Table `case_events`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `case_file_id` | `int4` |  Nullable |
| `firm_id` | `int4` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |
| `event_date` | `date` |  |
| `kind` | `varchar` |  |
| `title` | `varchar` |  |
| `notes` | `text` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |
| `purpose` | `varchar` |  Nullable |
| `outcome` | `text` |  Nullable |

## Table `case_documents`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `case_file_id` | `int4` |  Nullable |
| `event_id` | `int4` |  Nullable |
| `uploaded_by_user_id` | `int4` |  Nullable |
| `title` | `varchar` |  |
| `doc_type` | `varchar` |  |
| `file_name` | `varchar` |  Nullable |
| `mime_type` | `varchar` |  Nullable |
| `size_bytes` | `int4` |  Nullable |
| `storage_path` | `varchar` |  |
| `description` | `text` |  Nullable |
| `created_at` | `timestamp` |  Nullable |

## Table `case_stage_changes`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `case_file_id` | `int4` |  Nullable |
| `from_stage` | `varchar` |  Nullable |
| `to_stage` | `varchar` |  Nullable |
| `changed_by_user_id` | `int4` |  Nullable |
| `changed_at` | `timestamp` |  Nullable |

## Table `case_expenses`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `case_file_id` | `int4` |  Nullable |
| `expense_date` | `date` |  Nullable |
| `description` | `varchar` |  |
| `category` | `varchar` |  Nullable |
| `amount` | `numeric` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |
| `created_at` | `timestamp` |  Nullable |

## Table `leads`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |
| `contact_name` | `varchar` |  |
| `phone` | `varchar` |  Nullable |
| `email` | `varchar` |  Nullable |
| `matter_summary` | `text` |  Nullable |
| `intake_notes` | `text` |  Nullable |
| `status` | `varchar` |  |
| `decided_at` | `timestamp` |  Nullable |
| `converted_case_file_id` | `int4` |  Nullable |
| `created_at` | `timestamp` |  Nullable |

## Table `case_notes`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `case_file_id` | `int4` |  Nullable |
| `body` | `text` |  |
| `pinned` | `bool` |  |
| `event_id` | `int4` |  Nullable |
| `document_id` | `int4` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |

## Table `case_exhibits`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `case_file_id` | `int4` |  Nullable |
| `exhibit_mark` | `varchar` |  Nullable |
| `description` | `varchar` |  Nullable |
| `party` | `varchar` |  Nullable |
| `status` | `varchar` |  |
| `document_id` | `int4` |  Nullable |
| `hearing_event_id` | `int4` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |
| `created_at` | `timestamp` |  Nullable |

## Table `tasks`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |
| `title` | `varchar` |  |
| `due_date` | `date` |  Nullable |
| `case_file_id` | `int4` |  Nullable |
| `done` | `bool` |  |
| `priority` | `varchar` |  |
| `created_at` | `timestamp` |  Nullable |

## Table `templates`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |
| `name` | `varchar` |  |
| `category` | `varchar` |  Nullable |
| `body` | `text` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |

## Table `drafts`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `firm_id` | `int4` |  Nullable |
| `created_by_user_id` | `int4` |  Nullable |
| `title` | `varchar` |  |
| `body` | `text` |  Nullable |
| `case_file_id` | `int4` |  Nullable |
| `template_id` | `int4` |  Nullable |
| `created_at` | `timestamp` |  Nullable |
| `updated_at` | `timestamp` |  Nullable |

