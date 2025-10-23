"""Seed database with sample data"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.main import create_app
from backend.app.models.models import db, Client, Invoice, InvoiceItem
from datetime import datetime, timedelta
import random

# Sample data
CLIENTS = [
    {
        "name": "Sharma & Associates",
        "email": "contact@sharma-law.com",
        "phone": "+91-98765-43210",
        "address": "123 Legal Plaza\nConnaught Place\nNew Delhi - 110001",
        "tax_id": "GSTIN123456789",
        "default_tax_rate": 18.0
    },
    {
        "name": "Tech Solutions Pvt Ltd",
        "email": "legal@techsolutions.in",
        "phone": "+91-98765-43211",
        "address": "45 Tech Park\nWhitefield\nBangalore - 560066",
        "tax_id": "GSTIN234567890",
        "default_tax_rate": 18.0
    },
    {
        "name": "Mumbai Enterprises",
        "email": "info@mumbai-ent.com",
        "phone": "+91-98765-43212",
        "address": "78 Business Center\nBandra West\nMumbai - 400050",
        "tax_id": "GSTIN345678901",
        "default_tax_rate": 18.0
    },
    {
        "name": "Global Trading Company",
        "email": "legal@globaltrading.in",
        "phone": "+91-98765-43213",
        "address": "90 Commerce Street\nSalt Lake\nKolkata - 700091",
        "tax_id": "GSTIN456789012",
        "default_tax_rate": 18.0
    },
    {
        "name": "Green Energy Solutions",
        "email": "contact@greenenergy.in",
        "phone": "+91-98765-43214",
        "address": "12 Eco Park\nGachibowli\nHyderabad - 500032",
        "tax_id": "GSTIN567890123",
        "default_tax_rate": 18.0
    },
    {
        "name": "City Builders Ltd",
        "email": "legal@citybuilders.in",
        "phone": "+91-98765-43215",
        "address": "34 Construction Avenue\nVastrapur\nAhmedabad - 380015",
        "tax_id": "GSTIN678901234",
        "default_tax_rate": 18.0
    },
    {
        "name": "Healthcare Associates",
        "email": "admin@healthcareassoc.in",
        "phone": "+91-98765-43216",
        "address": "56 Medical Plaza\nKoramangala\nBangalore - 560034",
        "tax_id": "GSTIN789012345",
        "default_tax_rate": 18.0
    },
    {
        "name": "Digital Marketing Pro",
        "email": "hello@digitalmarketingpro.in",
        "phone": "+91-98765-43217",
        "address": "23 Creative Hub\nIndiranagar\nBangalore - 560038",
        "tax_id": "GSTIN890123456",
        "default_tax_rate": 18.0
    },
    {
        "name": "Financial Services Corp",
        "email": "contact@finservices.in",
        "phone": "+91-98765-43218",
        "address": "67 Finance Tower\nNariman Point\nMumbai - 400021",
        "tax_id": "GSTIN901234567",
        "default_tax_rate": 18.0
    },
    {
        "name": "Education Solutions Ltd",
        "email": "info@edusolut ions.in",
        "phone": "+91-98765-43219",
        "address": "89 Knowledge Park\nElectronic City\nBangalore - 560100",
        "tax_id": "GSTIN012345678",
        "default_tax_rate": 18.0
    }
]

SERVICES = [
    ("Legal Consultation - Contract Review", 15000, 25000),
    ("Corporate Law Advisory Services", 30000, 50000),
    ("Intellectual Property Registration", 20000, 40000),
    ("Litigation Support Services", 25000, 60000),
    ("Tax Advisory and Compliance", 18000, 35000),
    ("Mergers and Acquisitions Advisory", 50000, 100000),
    ("Employment Law Consultation", 12000, 25000),
    ("Real Estate Legal Services", 20000, 45000),
    ("Regulatory Compliance Review", 15000, 30000),
    ("Legal Due Diligence", 25000, 55000),
    ("Trademark Registration and Protection", 10000, 20000),
    ("Contract Drafting Services", 8000, 18000),
]


def seed_database():
    """Seed the database with sample data"""
    app = create_app()
    
    with app.app_context():
        print("🌱 Seeding database...")
        
        # Clear existing data (optional - comment out to preserve data)
        print("  Clearing existing data...")
        InvoiceItem.query.delete()
        Invoice.query.delete()
        Client.query.delete()
        db.session.commit()
        
        # Create clients
        print("  Creating 10 clients...")
        clients = []
        for client_data in CLIENTS:
            client = Client(**client_data)
            db.session.add(client)
            clients.append(client)
        
        db.session.commit()
        print(f"  ✓ Created {len(clients)} clients")
        
        # Create invoices over the last 12 months
        print("  Creating 20 invoices spanning last 12 months...")
        invoices = []
        
        for i in range(20):
            # Random client
            client = random.choice(clients)
            
            # Random date in last 12 months
            days_ago = random.randint(0, 365)
            invoice_date = datetime.now().date() - timedelta(days=days_ago)
            due_date = invoice_date + timedelta(days=random.choice([15, 30, 45]))
            
            # Generate invoice number
            year = invoice_date.year
            invoice_number = f"LAW/{year}/{str(i+1).zfill(4)}"
            
            # Random status (70% paid, 20% sent, 10% draft)
            status_choice = random.random()
            if status_choice < 0.7:
                status = 'paid'
                paid_date = invoice_date + timedelta(days=random.randint(1, 30))
            elif status_choice < 0.9:
                status = 'sent'
                paid_date = None
            else:
                status = 'draft'
                paid_date = None
            
            # Create invoice
            invoice = Invoice(
                invoice_number=invoice_number,
                client_id=client.id,
                invoice_date=invoice_date,
                due_date=due_date,
                short_desc=random.choice(SERVICES)[0],
                tax_rate=client.default_tax_rate,
                status=status,
                paid_date=paid_date,
                notes="Thank you for your business!"
            )
            
            # Add 1-3 line items
            num_items = random.randint(1, 3)
            for _ in range(num_items):
                service, min_price, max_price = random.choice(SERVICES)
                rate = random.randint(min_price, max_price)
                quantity = random.choice([1, 2, 1, 1, 1])  # Mostly 1
                
                item = InvoiceItem(
                    description=service,
                    quantity=quantity,
                    rate=rate,
                    amount=rate * quantity
                )
                invoice.items.append(item)
            
            # Calculate totals
            invoice.calculate_totals()
            
            db.session.add(invoice)
            invoices.append(invoice)
        
        db.session.commit()
        print(f"  ✓ Created {len(invoices)} invoices")
        
        # Print summary
        print("\n✅ Database seeded successfully!")
        print(f"\n📊 Summary:")
        print(f"   Clients: {Client.query.count()}")
        print(f"   Invoices: {Invoice.query.count()}")
        print(f"   - Draft: {Invoice.query.filter_by(status='draft').count()}")
        print(f"   - Sent: {Invoice.query.filter_by(status='sent').count()}")
        print(f"   - Paid: {Invoice.query.filter_by(status='paid').count()}")
        print(f"   Invoice Items: {InvoiceItem.query.count()}")
        
        # Calculate total revenue
        total_revenue = db.session.query(db.func.sum(Invoice.total)).filter(
            Invoice.status.in_(['paid', 'sent'])
        ).scalar() or 0
        print(f"   Total Revenue: ₹{total_revenue:,.2f}")


if __name__ == '__main__':
    seed_database()
