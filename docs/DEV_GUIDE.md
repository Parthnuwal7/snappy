# SNAPPY Developer Guide

## Architecture Overview

SNAPPY follows a **local-first architecture** with a Flask backend serving as the API layer and React frontend providing the user interface. The application can run standalone or be packaged with Tauri for native desktop distribution.

## Technology Stack

### Backend (Flask)
- **Flask 3.0** - Web framework
- **SQLAlchemy 2.0** - ORM for SQLite
- **WeasyPrint** - HTML to PDF conversion
- **DuckDB** - Analytics engine
- **RapidFuzz** - Fuzzy string matching

### Frontend (React)
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Query** - Server state management
- **React Hook Form** - Form handling
- **Recharts** - Data visualization

### Desktop (Tauri)
- **Tauri 1.5** - Native app wrapper
- **Rust** - System-level operations

## Application Flow

```
┌─────────────┐         ┌─────────────┐         ┌──────────────┐
│   React     │ <-----> │   Flask     │ <-----> │   SQLite     │
│   Frontend  │   HTTP  │   Backend   │         │   Database   │
│  (Port 5173)│         │ (Port 5000) │         │  (snappy.db) │
└─────────────┘         └─────────────┘         └──────────────┘
                               │
                               │
                        ┌──────▼──────┐
                        │   DuckDB    │
                        │  Analytics  │
                        └─────────────┘
```

## Backend Architecture

### Application Factory Pattern

The Flask application uses the factory pattern for testability and configuration flexibility:

```python
# backend/app/main.py
def create_app():
    app = Flask(__name__)
    # Configure app
    db.init_app(app)
    # Register blueprints
    app.register_blueprint(clients.bp)
    return app
```

### Database Models

Located in `backend/app/models/models.py`:

- **Client**: Customer information
- **Invoice**: Invoice header data
- **InvoiceItem**: Line items for each invoice
- **Settings**: Application configuration

### API Structure

All API endpoints are organized in blueprints under `backend/app/api/`:

- `clients.py` - Client CRUD operations
- `invoices.py` - Invoice management
- `analytics.py` - DuckDB-powered analytics
- `import_csv.py` - CSV import with fuzzy matching
- `backup.py` - Backup and restore operations

### Services Layer

Business logic is separated into services:

- **pdf_service.py**: Invoice PDF generation using WeasyPrint
- **duckdb_service.py**: Analytics queries
- **backup_service.py**: Encryption/decryption for backups

## Frontend Architecture

### React Router Structure

```tsx
<Router>
  <Route path="/" element={<Layout />}>
    <Route path="dashboard" element={<Dashboard />} />
    <Route path="invoices" element={<InvoiceList />} />
    <Route path="invoices/new" element={<NewInvoice />} />
    <Route path="clients" element={<Clients />} />
    <Route path="reports" element={<Reports />} />
    <Route path="settings" element={<Settings />} />
  </Route>
</Router>
```

### State Management

- **React Query**: Server state (invoices, clients, analytics)
- **React Hook Form**: Form state with validation
- **Local State**: UI state (modals, filters)

### API Layer

Centralized API client in `frontend/src/api.ts`:

```typescript
export const api = {
  getInvoices: (filters) => fetchAPI('/api/invoices', filters),
  createInvoice: (data) => fetchAPI('/api/invoices', { method: 'POST', body: data }),
  // ...
};
```

## Database Schema

### Relationships

```
┌─────────────┐       ┌──────────────┐       ┌──────────────────┐
│   Clients   │ 1   * │   Invoices   │ 1   * │  Invoice Items   │
│             │◄──────┤              │◄──────┤                  │
│ - id        │       │ - id         │       │ - id             │
│ - name      │       │ - client_id  │       │ - invoice_id     │
│ - email     │       │ - invoice_no │       │ - description    │
│ - ...       │       │ - total      │       │ - quantity       │
└─────────────┘       │ - status     │       │ - rate           │
                      └──────────────┘       │ - amount         │
                                             └──────────────────┘
```

### Invoice Status Flow

```
draft → sent → paid
  │              │
  └─────────────→ void
```

## PDF Generation Flow

1. Frontend renders invoice HTML template
2. POST request to `/api/invoices/{id}/generate_pdf`
3. Backend fetches invoice data with relationships
4. Jinja2 template renders HTML with invoice data
5. WeasyPrint converts HTML to PDF bytes
6. PDF returned as downloadable file

### Customizing PDF Template

Edit the `INVOICE_TEMPLATE` constant in `backend/app/services/pdf_service.py`. The template uses Tailwind-inspired inline styles.

## Analytics with DuckDB

DuckDB provides high-performance analytics on invoice data:

### Sync Process

```python
def sync_invoices():
    # 1. Query SQLite for invoice data
    invoices = Invoice.query.join(Client).all()
    
    # 2. Transform to dict format
    data = [serialize(inv) for inv in invoices]
    
    # 3. Load into DuckDB
    conn.execute("CREATE TABLE invoices AS SELECT * FROM data")
```

### Analytics Queries

```python
def get_monthly_revenue():
    return conn.execute("""
        SELECT 
            strftime(invoice_date, '%Y-%m') as month,
            SUM(total) as revenue
        FROM invoices
        WHERE status != 'void'
        GROUP BY month
    """).fetchall()
```

## CSV Import

### Import Flow

1. Frontend uploads CSV file
2. Backend reads with pandas
3. Fuzzy matching against existing data using RapidFuzz
4. Preview duplicates and conflicts
5. User confirms import
6. Data inserted into SQLite

### Fuzzy Matching Example

```python
from rapidfuzz import fuzz, process

existing_names = [c.name for c in Client.query.all()]
matches = process.extractOne(
    csv_name, 
    existing_names, 
    scorer=fuzz.ratio
)

if matches[1] > 85:  # 85% similarity
    # Flag as duplicate
```

## Backup & Restore

### Encryption

Uses **Fernet (AES-256)** with PBKDF2 key derivation:

```python
def encrypt_backup(data: bytes, password: str) -> bytes:
    salt = os.urandom(16)
    key = derive_key(password, salt)
    f = Fernet(key)
    encrypted = f.encrypt(data)
    return salt + encrypted  # Prepend salt
```

### Backup Process

1. Read SQLite database file
2. Optionally encrypt with password
3. Return as downloadable `.db` or `.enc` file

### Restore Process

1. Upload backup file
2. Decrypt if encrypted
3. Validate database schema
4. Create backup of current DB
5. Replace with restored data

## Keyboard Shortcuts

Implemented using window event listeners:

```typescript
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    const modKey = isMac ? e.metaKey : e.ctrlKey;
    
    if (modKey && e.key === 'n') {
      navigate('/invoices/new');
    }
  };
  
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, []);
```

## Tauri Integration (Pending)

### Communication Flow

```
┌─────────────┐                    ┌──────────────┐
│   React     │  Tauri Commands    │   Rust       │
│   Frontend  │ ◄─────────────────►│   Backend    │
│             │                    │              │
└─────────────┘                    └──────────────┘
       │                                  │
       └────────► HTTP ◄──────────────────┘
              (Flask Server)
```

### Planned Implementation

1. Tauri spawns Flask process on app start
2. React communicates with Flask via localhost
3. Tauri handles system integration (file dialogs, notifications)
4. Bundle Python + dependencies with PyInstaller

## Building for Production

### Frontend Build

```bash
cd frontend
npm run build
```

Outputs to `frontend/dist/` with optimized assets.

### Backend Packaging (Future)

Using PyInstaller to bundle Python:

```bash
pyinstaller --onefile --add-data "app:app" backend/app/main.py
```

### Tauri Build (Future)

```bash
cd frontend
npm run tauri:build
```

Produces platform-specific installers:
- Windows: `.msi`, `.exe`
- macOS: `.dmg`, `.app`
- Linux: `.deb`, `.AppImage`

## Testing Strategy

### Backend Tests

```python
# backend/tests/test_invoices.py
def test_create_invoice(client):
    response = client.post('/api/invoices', json={
        'client_id': 1,
        'invoice_date': '2025-01-20',
        'items': [...]
    })
    assert response.status_code == 201
    assert 'invoice_number' in response.json
```

### Running Tests

```bash
cd backend
pytest -v
```

## Performance Optimization

### Backend
- Database indexes on frequently queried columns
- DuckDB for analytics (faster than SQLite aggregations)
- Lazy loading of relationships
- Connection pooling

### Frontend
- React Query caching
- Code splitting with dynamic imports
- Virtualized lists for large datasets
- Debounced search inputs

## Security Considerations

### Local-First Security
- No remote data transmission by default
- Encrypted backups with strong passwords
- PIN protection for app access (optional)
- No embedded API keys or secrets

### Input Validation
- Backend: Flask-WTF forms or manual validation
- Frontend: React Hook Form with schema validation
- SQL injection protection via SQLAlchemy ORM

## Troubleshooting

### Common Issues

**Flask not starting:**
```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -r requirements.txt
```

**Frontend build errors:**
```bash
# Clear cache
rm -rf node_modules
npm install
```

**Database locked:**
```bash
# Close all connections, restart Flask
```

## Contributing Guidelines

1. **Code Style**
   - Python: Black formatter, flake8 linter
   - TypeScript: Prettier, ESLint

2. **Commit Messages**
   - Format: `type(scope): description`
   - Example: `feat(invoices): add bulk export`

3. **Pull Requests**
   - Include tests
   - Update documentation
   - Keep PRs focused and small

## Deployment

### Self-Hosting

1. Clone repository
2. Follow installation steps in README
3. Run with `scripts/dev.bat` or production server (Waitress/Gunicorn)

### Future: Cloud Deploy (Optional)

While SNAPPY is local-first, optional cloud sync could be added:
- Deploy Flask to Docker container
- PostgreSQL instead of SQLite
- S3 for PDF storage
- Redis for caching

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Query](https://tanstack.com/query/)
- [WeasyPrint](https://weasyprint.org/)
- [DuckDB](https://duckdb.org/)
- [Tauri](https://tauri.app/)

## Support

For questions or issues:
- GitHub Issues
- Developer docs in `/docs`
- Code comments throughout codebase

---

**Happy Coding!** 🚀
