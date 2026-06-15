1.
[
  {
    "table_name": "bank_accounts",
    "column_name": "id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": "nextval('bank_accounts_id_seq'::regclass)"
  },
  {
    "table_name": "bank_accounts",
    "column_name": "user_id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "bank_accounts",
    "column_name": "bank_name",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "bank_accounts",
    "column_name": "account_number",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "bank_accounts",
    "column_name": "account_holder_name",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "bank_accounts",
    "column_name": "ifsc_code",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "bank_accounts",
    "column_name": "upi_id",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "bank_accounts",
    "column_name": "upi_qr_path",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "bank_accounts",
    "column_name": "is_default",
    "data_type": "boolean",
    "udt_name": "bool",
    "is_nullable": "YES",
    "column_default": "true"
  },
  {
    "table_name": "bank_accounts",
    "column_name": "created_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "bank_accounts",
    "column_name": "updated_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "clients",
    "column_name": "id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": "nextval('clients_id_seq'::regclass)"
  },
  {
    "table_name": "clients",
    "column_name": "user_id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "clients",
    "column_name": "name",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "clients",
    "column_name": "email",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "clients",
    "column_name": "phone",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "clients",
    "column_name": "address",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "clients",
    "column_name": "tax_id",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "clients",
    "column_name": "default_tax_rate",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "18.0"
  },
  {
    "table_name": "clients",
    "column_name": "notes",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "clients",
    "column_name": "created_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "clients",
    "column_name": "updated_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "firm_details",
    "column_name": "id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": "nextval('firm_details_id_seq'::regclass)"
  },
  {
    "table_name": "firm_details",
    "column_name": "user_id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "firm_name",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "firm_address",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "firm_email",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "firm_phone",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "firm_phone_2",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "firm_website",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "logo_path",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "signature_path",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "terms_and_conditions",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "billing_terms",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "firm_details",
    "column_name": "default_template",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": "'Simple'::character varying"
  },
  {
    "table_name": "firm_details",
    "column_name": "invoice_prefix",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": "'INV'::character varying"
  },
  {
    "table_name": "firm_details",
    "column_name": "default_tax_rate",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "18.0"
  },
  {
    "table_name": "firm_details",
    "column_name": "currency",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": "'INR'::character varying"
  },
  {
    "table_name": "firm_details",
    "column_name": "show_due_date",
    "data_type": "boolean",
    "udt_name": "bool",
    "is_nullable": "YES",
    "column_default": "true"
  },
  {
    "table_name": "firm_details",
    "column_name": "created_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "firm_details",
    "column_name": "updated_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "firm_details",
    "column_name": "use_invoice_prefix",
    "data_type": "boolean",
    "udt_name": "bool",
    "is_nullable": "YES",
    "column_default": "true"
  },
  {
    "table_name": "invoice_items",
    "column_name": "id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": "nextval('invoice_items_id_seq'::regclass)"
  },
  {
    "table_name": "invoice_items",
    "column_name": "invoice_id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "invoice_items",
    "column_name": "description",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "invoice_items",
    "column_name": "quantity",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "1"
  },
  {
    "table_name": "invoice_items",
    "column_name": "rate",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "0"
  },
  {
    "table_name": "invoice_items",
    "column_name": "amount",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "0"
  },
  {
    "table_name": "invoices",
    "column_name": "id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": "nextval('invoices_id_seq'::regclass)"
  },
  {
    "table_name": "invoices",
    "column_name": "user_id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "invoices",
    "column_name": "client_id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "invoices",
    "column_name": "invoice_number",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "invoices",
    "column_name": "invoice_date",
    "data_type": "date",
    "udt_name": "date",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "invoices",
    "column_name": "due_date",
    "data_type": "date",
    "udt_name": "date",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "invoices",
    "column_name": "short_desc",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "invoices",
    "column_name": "subtotal",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "0"
  },
  {
    "table_name": "invoices",
    "column_name": "tax_rate",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "18.0"
  },
  {
    "table_name": "invoices",
    "column_name": "tax_amount",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "0"
  },
  {
    "table_name": "invoices",
    "column_name": "total",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "0"
  },
  {
    "table_name": "invoices",
    "column_name": "status",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": "'draft'::character varying"
  },
  {
    "table_name": "invoices",
    "column_name": "paid_date",
    "data_type": "date",
    "udt_name": "date",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "invoices",
    "column_name": "notes",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "invoices",
    "column_name": "signature_path",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "invoices",
    "column_name": "created_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "invoices",
    "column_name": "updated_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "items",
    "column_name": "id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": "nextval('items_id_seq'::regclass)"
  },
  {
    "table_name": "items",
    "column_name": "user_id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "items",
    "column_name": "name",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "items",
    "column_name": "alias",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "items",
    "column_name": "description",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "items",
    "column_name": "default_rate",
    "data_type": "numeric",
    "udt_name": "numeric",
    "is_nullable": "YES",
    "column_default": "0.0"
  },
  {
    "table_name": "items",
    "column_name": "unit",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "items",
    "column_name": "hsn_code",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "items",
    "column_name": "is_active",
    "data_type": "boolean",
    "udt_name": "bool",
    "is_nullable": "YES",
    "column_default": "true"
  },
  {
    "table_name": "items",
    "column_name": "created_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "items",
    "column_name": "updated_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "settings",
    "column_name": "id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": "nextval('settings_id_seq'::regclass)"
  },
  {
    "table_name": "settings",
    "column_name": "user_id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "settings",
    "column_name": "key",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "settings",
    "column_name": "value",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "settings",
    "column_name": "updated_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "users",
    "column_name": "id",
    "data_type": "integer",
    "udt_name": "int4",
    "is_nullable": "NO",
    "column_default": "nextval('users_id_seq'::regclass)"
  },
  {
    "table_name": "users",
    "column_name": "supabase_id",
    "data_type": "uuid",
    "udt_name": "uuid",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "users",
    "column_name": "email",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "NO",
    "column_default": null
  },
  {
    "table_name": "users",
    "column_name": "password_hash",
    "data_type": "character varying",
    "udt_name": "varchar",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "users",
    "column_name": "is_active",
    "data_type": "boolean",
    "udt_name": "bool",
    "is_nullable": "YES",
    "column_default": "true"
  },
  {
    "table_name": "users",
    "column_name": "is_onboarded",
    "data_type": "boolean",
    "udt_name": "bool",
    "is_nullable": "YES",
    "column_default": "false"
  },
  {
    "table_name": "users",
    "column_name": "device_id",
    "data_type": "text",
    "udt_name": "text",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "users",
    "column_name": "device_info",
    "data_type": "jsonb",
    "udt_name": "jsonb",
    "is_nullable": "YES",
    "column_default": null
  },
  {
    "table_name": "users",
    "column_name": "created_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "users",
    "column_name": "updated_at",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": "now()"
  },
  {
    "table_name": "users",
    "column_name": "last_login",
    "data_type": "timestamp without time zone",
    "udt_name": "timestamp",
    "is_nullable": "YES",
    "column_default": null
  }
]

2. 
[
  {
    "conname": "users_email_key",
    "tbl": "users",
    "def": "UNIQUE (email)"
  },
  {
    "conname": "users_pkey",
    "tbl": "users",
    "def": "PRIMARY KEY (id)"
  },
  {
    "conname": "users_supabase_id_key",
    "tbl": "users",
    "def": "UNIQUE (supabase_id)"
  },
  {
    "conname": "firm_details_pkey",
    "tbl": "firm_details",
    "def": "PRIMARY KEY (id)"
  },
  {
    "conname": "firm_details_user_id_fkey",
    "tbl": "firm_details",
    "def": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
  },
  {
    "conname": "firm_details_user_id_key",
    "tbl": "firm_details",
    "def": "UNIQUE (user_id)"
  },
  {
    "conname": "bank_accounts_pkey",
    "tbl": "bank_accounts",
    "def": "PRIMARY KEY (id)"
  },
  {
    "conname": "bank_accounts_user_id_fkey",
    "tbl": "bank_accounts",
    "def": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
  },
  {
    "conname": "clients_pkey",
    "tbl": "clients",
    "def": "PRIMARY KEY (id)"
  },
  {
    "conname": "clients_user_id_fkey",
    "tbl": "clients",
    "def": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
  },
  {
    "conname": "items_pkey",
    "tbl": "items",
    "def": "PRIMARY KEY (id)"
  },
  {
    "conname": "items_user_id_fkey",
    "tbl": "items",
    "def": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
  },
  {
    "conname": "invoices_client_id_fkey",
    "tbl": "invoices",
    "def": "FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT"
  },
  {
    "conname": "invoices_pkey",
    "tbl": "invoices",
    "def": "PRIMARY KEY (id)"
  },
  {
    "conname": "invoices_user_id_fkey",
    "tbl": "invoices",
    "def": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
  },
  {
    "conname": "invoice_items_invoice_id_fkey",
    "tbl": "invoice_items",
    "def": "FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE"
  },
  {
    "conname": "invoice_items_pkey",
    "tbl": "invoice_items",
    "def": "PRIMARY KEY (id)"
  },
  {
    "conname": "settings_pkey",
    "tbl": "settings",
    "def": "PRIMARY KEY (id)"
  },
  {
    "conname": "settings_user_id_fkey",
    "tbl": "settings",
    "def": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
  },
  {
    "conname": "settings_user_id_key_key",
    "tbl": "settings",
    "def": "UNIQUE (user_id, key)"
  }
]

3.
[
  {
    "indexname": "bank_accounts_pkey",
    "tablename": "bank_accounts",
    "indexdef": "CREATE UNIQUE INDEX bank_accounts_pkey ON public.bank_accounts USING btree (id)"
  },
  {
    "indexname": "idx_bank_accounts_user_id",
    "tablename": "bank_accounts",
    "indexdef": "CREATE INDEX idx_bank_accounts_user_id ON public.bank_accounts USING btree (user_id)"
  },
  {
    "indexname": "clients_pkey",
    "tablename": "clients",
    "indexdef": "CREATE UNIQUE INDEX clients_pkey ON public.clients USING btree (id)"
  },
  {
    "indexname": "idx_clients_user_id",
    "tablename": "clients",
    "indexdef": "CREATE INDEX idx_clients_user_id ON public.clients USING btree (user_id)"
  },
  {
    "indexname": "firm_details_pkey",
    "tablename": "firm_details",
    "indexdef": "CREATE UNIQUE INDEX firm_details_pkey ON public.firm_details USING btree (id)"
  },
  {
    "indexname": "firm_details_user_id_key",
    "tablename": "firm_details",
    "indexdef": "CREATE UNIQUE INDEX firm_details_user_id_key ON public.firm_details USING btree (user_id)"
  },
  {
    "indexname": "idx_firm_details_user_id",
    "tablename": "firm_details",
    "indexdef": "CREATE INDEX idx_firm_details_user_id ON public.firm_details USING btree (user_id)"
  },
  {
    "indexname": "idx_invoice_items_invoice_id",
    "tablename": "invoice_items",
    "indexdef": "CREATE INDEX idx_invoice_items_invoice_id ON public.invoice_items USING btree (invoice_id)"
  },
  {
    "indexname": "invoice_items_pkey",
    "tablename": "invoice_items",
    "indexdef": "CREATE UNIQUE INDEX invoice_items_pkey ON public.invoice_items USING btree (id)"
  },
  {
    "indexname": "idx_invoices_client_id",
    "tablename": "invoices",
    "indexdef": "CREATE INDEX idx_invoices_client_id ON public.invoices USING btree (client_id)"
  },
  {
    "indexname": "idx_invoices_user_id",
    "tablename": "invoices",
    "indexdef": "CREATE INDEX idx_invoices_user_id ON public.invoices USING btree (user_id)"
  },
  {
    "indexname": "invoices_pkey",
    "tablename": "invoices",
    "indexdef": "CREATE UNIQUE INDEX invoices_pkey ON public.invoices USING btree (id)"
  },
  {
    "indexname": "idx_items_user_id",
    "tablename": "items",
    "indexdef": "CREATE INDEX idx_items_user_id ON public.items USING btree (user_id)"
  },
  {
    "indexname": "items_pkey",
    "tablename": "items",
    "indexdef": "CREATE UNIQUE INDEX items_pkey ON public.items USING btree (id)"
  },
  {
    "indexname": "idx_settings_user_id",
    "tablename": "settings",
    "indexdef": "CREATE INDEX idx_settings_user_id ON public.settings USING btree (user_id)"
  },
  {
    "indexname": "settings_pkey",
    "tablename": "settings",
    "indexdef": "CREATE UNIQUE INDEX settings_pkey ON public.settings USING btree (id)"
  },
  {
    "indexname": "settings_user_id_key_key",
    "tablename": "settings",
    "indexdef": "CREATE UNIQUE INDEX settings_user_id_key_key ON public.settings USING btree (user_id, key)"
  },
  {
    "indexname": "users_email_key",
    "tablename": "users",
    "indexdef": "CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email)"
  },
  {
    "indexname": "users_pkey",
    "tablename": "users",
    "indexdef": "CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id)"
  },
  {
    "indexname": "users_supabase_id_key",
    "tablename": "users",
    "indexdef": "CREATE UNIQUE INDEX users_supabase_id_key ON public.users USING btree (supabase_id)"
  }
]