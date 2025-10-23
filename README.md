# SNAPPY - Local-First Desktop Billing App

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

SNAPPY is a powerful, local-first desktop billing and invoicing application designed specifically for lawyers and professionals. Built with **Tauri**, **React**, and **Flask**, it prioritizes speed, clean keyboard-first UX, robust analytics, and small bundle size.

## ✨ Features

- 📄 **Invoice Management** - Create, edit, and manage invoices with ease
- 👥 **Client Management** - Maintain detailed client records
- 📊 **Analytics Dashboard** - Real-time insights with monthly revenue trends, top clients, and aging analysis
- 🔍 **Fuzzy Search** - Fast client lookup with intelligent matching
- 📈 **DuckDB Analytics** - High-performance analytics engine
- 💾 **Backup & Restore** - Encrypted backups with password protection
- 📥 **CSV Import** - Import clients and invoices with duplicate detection
- 🎨 **PDF Generation** - Beautiful, customizable invoice PDFs
- ⌨️ **Keyboard Shortcuts** - Keyboard-first design for power users
- 🗄️ **SQLite Database** - Reliable local-first storage

## 🎯 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Git**

### One-Command Setup

**Windows:**
```cmd
scripts\dev.bat
```

**Linux/macOS:**
```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

This will:
1. Create Python virtual environment and install dependencies
2. Install frontend dependencies
3. Start Flask backend on http://localhost:5000
4. Start React frontend on http://localhost:5173

## 📦 Manual Installation

### Backend Setup

```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` file from `.env.example`:
```cmd
copy .env.example .env
```

### Frontend Setup

```cmd
cd frontend
npm install
```

### Seed Database (Optional)

```cmd
python scripts\seed_db.py
```

This creates 10 sample clients and 20 invoices spanning the last 12 months.

## 🚀 Running the Application

### Development Mode

**Start Backend:**
```cmd
cd backend
venv\Scripts\activate
set FLASK_APP=app\main.py
set FLASK_ENV=development
python -m flask run --port=5000
```

**Start Frontend:**
```cmd
cd frontend
npm run dev
```

Access the application at: http://localhost:5173

### Production Build

```cmd
cd frontend
npm run build
```

## 📚 API Documentation

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### Clients
- `GET /clients` - List all clients (supports `?search=` parameter)
- `GET /clients/{id}` - Get client details
- `POST /clients` - Create new client
- `PUT /clients/{id}` - Update client
- `DELETE /clients/{id}` - Delete client

#### Invoices
- `GET /invoices` - List invoices (filters: `client_id`, `status`, `start_date`, `end_date`, `search`)
- `GET /invoices/{id}` - Get invoice with items
- `POST /invoices` - Create new invoice
- `PUT /invoices/{id}` - Update invoice
- `POST /invoices/{id}/mark_paid` - Mark invoice as paid
- `POST /invoices/{id}/generate_pdf` - Generate PDF
- `DELETE /invoices/{id}` - Void invoice

#### Analytics
- `GET /analytics/monthly` - Monthly revenue data
- `GET /analytics/top_clients` - Top clients by revenue
- `GET /analytics/aging` - Aging buckets for unpaid invoices

#### Import/Export
- `POST /import/csv` - Import clients or invoices from CSV
- `POST /backup` - Create database backup
- `POST /restore` - Restore from backup

### Example Request

**Create Invoice:**
```json
POST /api/invoices
{
  "client_id": 1,
  "invoice_date": "2025-01-20",
  "due_date": "2025-02-20",
  "short_desc": "Legal consultation services",
  "tax_rate": 18.0,
  "items": [
    {
      "description": "Contract review and advisory",
      "quantity": 2,
      "rate": 15000,
      "amount": 30000
    }
  ]
}
```

## ⌨️ Keyboard Shortcuts

- `Ctrl/Cmd + N` - New Invoice
- `Ctrl/Cmd + S` - Save
- `Ctrl/Cmd + E` - Export PDF
- `Ctrl/Cmd + P` - Print
- `Ctrl/Cmd + K` - Focus Search

## 🏗️ Project Structure

```
snappy/
├── backend/                # Flask backend
│   ├── app/
│   │   ├── main.py        # Flask app factory
│   │   ├── api/           # API endpoints
│   │   ├── models/        # SQLAlchemy models
│   │   └── services/      # Business logic
│   ├── requirements.txt
│   └── tests/
├── frontend/              # React frontend
│   ├── src/
│   │   ├── pages/        # Page components
│   │   ├── components/   # Reusable components
│   │   ├── App.tsx
│   │   └── api.ts        # API client
│   ├── package.json
│   └── vite.config.ts
├── scripts/
│   ├── dev.bat           # Windows dev script
│   ├── dev.sh            # Linux/macOS dev script
│   └── seed_db.py        # Database seeder
├── src-tauri/            # Tauri configuration
├── .env.example          # Environment template
└── README.md
```

## 🗄️ Database Schema

### Clients Table
- `id` - Primary key
- `name` - Client name (required)
- `email`, `phone`, `address` - Contact details
- `tax_id` - Tax identification
- `default_tax_rate` - Default tax percentage
- `notes` - Additional notes

### Invoices Table
- `id` - Primary key
- `invoice_number` - Unique invoice number (LAW/YYYY/NNNN)
- `client_id` - Foreign key to clients
- `invoice_date`, `due_date` - Dates
- `short_desc` - Brief description
- `subtotal`, `tax_rate`, `tax_amount`, `total` - Amounts
- `status` - draft | sent | paid | void
- `signature_path` - Path to signature image

### Invoice Items Table
- `id` - Primary key
- `invoice_id` - Foreign key to invoices
- `description` - Item description
- `quantity`, `rate`, `amount` - Pricing details

## 🧪 Testing

### Backend Tests
```cmd
cd backend
pytest
```

### Linting
```cmd
# Backend
cd backend
black .
flake8 .

# Frontend
cd frontend
npm run lint
npm run format
```

## 📋 CSV Import Format

### Clients CSV
```csv
name,email,phone,address,tax_id,default_tax_rate
"Sharma & Associates","contact@sharma.com","+91-98765-43210","123 Legal Plaza, New Delhi","GSTIN123",18.0
```

### Invoices CSV
```csv
client_name,invoice_date,description,amount,quantity,tax_rate
"Sharma & Associates","2025-01-15","Legal consultation",25000,1,18.0
```

## 🔒 Security

- **Local-First**: No remote servers by default
- **Encrypted Backups**: AES-256 encryption with password
- **No Telemetry**: Zero data collection
- **APP PIN Lock**: Optional PIN protection (Settings)

## 🎨 Customization

### Invoice Template
Edit `backend/app/services/pdf_service.py` to customize the invoice HTML template with Tailwind CSS classes.

### Currency
Modify `.env`:
```
CURRENCY=INR
```

### Invoice Numbering
Update in Settings UI or `.env`:
```
INVOICE_PREFIX=LAW
```

## 🚧 Tauri Desktop Build

**Coming Soon** - Full Tauri integration for standalone desktop builds.

```cmd
cd frontend
npm run tauri:build
```

## 🤝 Contributing

This is an open-source project under the MIT License. Contributions are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Known Issues

- Tauri integration pending (currently web-based)
- E2E tests to be added
- CI/CD pipeline in progress

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions

## 🎯 Roadmap

- [ ] Complete Tauri desktop packaging
- [ ] E2E tests with Playwright
- [ ] Multi-currency support
- [ ] Email invoice delivery
- [ ] Recurring invoices
- [ ] Payment reminders
- [ ] Custom report builder
- [ ] Multi-language support

---

**Built with ❤️ for lawyers and professionals who value speed, privacy, and control.**
