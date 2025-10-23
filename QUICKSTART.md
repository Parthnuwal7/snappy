# 🚀 SNAPPY - Quick Start Guide

## Get Up and Running in 5 Minutes!

### Step 1: Install Dependencies

**Backend (Python):**
```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

**Frontend (Node.js):**
```cmd
cd frontend
npm install
cd ..
```

### Step 2: Set Up Environment

```cmd
copy .env.example .env
```

That's it! The defaults work perfectly for local development.

### Step 3: Seed Sample Data (Optional but Recommended)

```cmd
python scripts\seed_db.py
```

This creates:
- 10 sample clients
- 20 invoices spanning 12 months
- Mix of paid/unpaid/draft statuses

### Step 4: Start the Application

**Option A: Automatic (Recommended)**
```cmd
scripts\dev.bat
```

**Option B: Manual (Two terminals)**

Terminal 1 - Backend:
```cmd
cd backend
venv\Scripts\activate
set FLASK_APP=app\main.py
python -m flask run --port=5000
```

Terminal 2 - Frontend:
```cmd
cd frontend
npm run dev
```

### Step 5: Open Your Browser

Frontend: **http://localhost:5173**
Backend API: **http://localhost:5000**

---

## 🎯 First Actions

### 1. View the Dashboard
- Navigate to http://localhost:5173
- See monthly revenue charts
- View top clients
- Check aging buckets

### 2. Create Your First Client
- Click "Clients" in sidebar
- Click "+ Add Client"
- Fill in:
  - Name (required)
  - Email, Phone, Address
  - Tax ID
  - Default Tax Rate (e.g., 18%)
- Click "Create"

### 3. Create Your First Invoice
- Click "Invoices" → "+ New Invoice"
- Search for client (fuzzy search works!)
- Set invoice and due dates
- Add line items:
  - Description
  - Quantity
  - Rate
  - (Amount auto-calculates)
- Add notes if needed
- Click "Create Invoice"

### 4. Generate PDF
- Go to "Invoices" page
- Find your invoice
- Click "PDF" button
- Download and open!

### 5. View Analytics
- Return to "Dashboard"
- See your invoice in monthly chart
- Client appears in top clients
- Unpaid amounts in aging buckets

---

## ⌨️ Keyboard Shortcuts

- `Ctrl + K` - Focus search
- Navigate using arrow keys in tables
- `Tab` to move between form fields

---

## 🐛 Troubleshooting

### "Python not found"
Install Python 3.11+ from python.org

### "Node not found"
Install Node.js 18+ from nodejs.org

### "Port 5000 already in use"
Kill the process or change port in .env:
```
FLASK_RUN_PORT=5001
```

### "Database locked"
Close all backend instances and restart

### Frontend won't start
```cmd
cd frontend
rmdir /s /q node_modules
npm install
npm run dev
```

### Backend errors
```cmd
cd backend
venv\Scripts\activate
pip install --upgrade -r requirements.txt
```

---

## 📚 Next Steps

1. **Customize Invoice Template**
   - Edit `backend/app/services/pdf_service.py`
   - Modify the `INVOICE_TEMPLATE` HTML

2. **Import Existing Data**
   - Prepare CSV file (see README.md for format)
   - POST to `/api/import/csv`

3. **Backup Your Data**
   - POST to `/api/backup`
   - Download encrypted backup

4. **Read the Docs**
   - `README.md` - User guide
   - `docs/DEV_GUIDE.md` - Developer guide
   - `PROJECT_STATUS.md` - Implementation status

---

## 🎉 You're All Set!

SNAPPY is now running and ready to use. Explore the features:

- ✅ Create clients
- ✅ Generate invoices  
- ✅ Download PDFs
- ✅ Track payments
- ✅ View analytics
- ✅ Import data
- ✅ Backup database

**Happy Invoicing!** 💼

---

## 🆘 Need Help?

- Check `README.md` for detailed documentation
- Review `docs/DEV_GUIDE.md` for technical details
- Check `PROJECT_STATUS.md` for feature status
- Open an issue on GitHub

## 📞 API Examples

### Create Client via API
```bash
curl -X POST http://localhost:5000/api/clients \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Client","email":"test@example.com","default_tax_rate":18}'
```

### Create Invoice via API
```bash
curl -X POST http://localhost:5000/api/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "invoice_date": "2025-01-20",
    "items": [
      {"description": "Legal Services", "quantity": 1, "rate": 25000, "amount": 25000}
    ]
  }'
```

### Generate PDF via API
```bash
curl -X POST http://localhost:5000/api/invoices/1/generate_pdf --output invoice.pdf
```

---

**Made with ❤️ by SNAPPY** • MIT License • Local-First • Privacy-Focused
