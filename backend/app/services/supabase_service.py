"""
Supabase Database Service for SNAPPY Desktop App
Replaces DuckDB with cloud-based Supabase PostgreSQL
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseService:
    """Supabase database service for SNAPPY desktop app"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        self.license_id: Optional[int] = None
    
    def set_license_id(self, license_id: int):
        """Set the current license ID for scoped operations"""
        self.license_id = license_id
    
    # ==================== LICENSE OPERATIONS ====================
    
    def activate_license(self, license_key: str, machine_id: str) -> Optional[Dict]:
        """
        Activate a license key
        Returns license data if successful, None or raises exception if invalid
        
        Security checks:
        1. Key exists in database
        2. Admin has verified payment (admin_verified = true)
        3. Status is not 'rejected' or 'pending_verification'
        4. Not expired (if already activated)
        """
        try:
            # Get license by key
            response = self.supabase.table('licenses')\
                .select('*')\
                .eq('license_key', license_key)\
                .single()\
                .execute()
            
            if not response.data:
                raise Exception("Invalid license key")
            
            license_data = response.data
            
            # CRITICAL SECURITY CHECKS
            
            # 1. Check if payment is still pending
            if license_data['status'] == 'pending_verification':
                raise Exception("Payment verification pending. Please wait for admin approval.")
            
            # 2. Check if payment/license was rejected
            if license_data['status'] == 'rejected':
                reason = license_data.get('admin_notes', 'Payment rejected')
                raise Exception(f"License rejected: {reason}")
            
            # 3. Check if admin has verified the payment
            if not license_data['admin_verified']:
                raise Exception("License not verified by admin yet. Please contact support.")
            
            # 4. Check if already active and not expired
            if license_data['status'] == 'active' and license_data['expires_at']:
                expires_at = datetime.fromisoformat(license_data['expires_at'].replace('Z', '+00:00'))
                if expires_at > datetime.now():
                    # Already active and valid - allow reactivation (e.g., new device)
                    self.license_id = license_data['id']
                    
                    # Update last activation timestamp
                    self.supabase.table('licenses')\
                        .update({
                            'last_activated_at': datetime.utcnow().isoformat(),
                            'machine_id': machine_id
                        })\
                        .eq('id', license_data['id'])\
                        .execute()
                    
                    return license_data
                else:
                    raise Exception("License has expired. Please renew your subscription.")
            
            # 5. Activate license (first time activation)
            # Only possible if admin_verified = true AND status != rejected
            now = datetime.utcnow()
            expires = now + timedelta(days=365)  # 1 year validity
            
            update_data = {
                'status': 'active',
                'invoked_at': now.isoformat(),
                'expires_at': expires.isoformat(),
                'machine_id': machine_id,
                'last_activated_at': now.isoformat()
            }
            
            self.supabase.table('licenses')\
                .update(update_data)\
                .eq('id', license_data['id'])\
                .execute()
            
            self.license_id = license_data['id']
            return {**license_data, **update_data}
            
        except Exception as e:
            error_msg = str(e)
            print(f"License activation error: {error_msg}")
            # Re-raise with user-friendly message
            raise Exception(error_msg)
    
    def verify_license(self, license_key: str) -> bool:
        """
        Check if license is valid and not expired
        
        Returns True only if:
        - License exists
        - Admin verified
        - Status is 'active'
        - Not expired
        """
        try:
            response = self.supabase.table('licenses')\
                .select('status, admin_verified, expires_at')\
                .eq('license_key', license_key)\
                .single()\
                .execute()
            
            if not response.data:
                return False
            
            license_data = response.data
            
            # Must be admin verified
            if not license_data['admin_verified']:
                return False
            
            # Status must be active (not pending or rejected)
            if license_data['status'] != 'active':
                return False
            
            # Check expiry
            if license_data['expires_at']:
                expires_at = datetime.fromisoformat(license_data['expires_at'].replace('Z', '+00:00'))
                return expires_at > datetime.now()
            
            return False
        except:
            return False
    
    # ==================== CLIENT OPERATIONS ====================
    
    def get_clients(self) -> List[Dict]:
        """Get all clients for current license"""
        response = self.supabase.table('clients')\
            .select('*')\
            .eq('license_id', self.license_id)\
            .order('name')\
            .execute()
        return response.data or []
    
    def get_client(self, client_id: int) -> Optional[Dict]:
        """Get client by ID"""
        response = self.supabase.table('clients')\
            .select('*')\
            .eq('id', client_id)\
            .eq('license_id', self.license_id)\
            .single()\
            .execute()
        return response.data
    
    def create_client(self, client_data: Dict) -> Dict:
        """Create new client"""
        client_data['license_id'] = self.license_id
        response = self.supabase.table('clients')\
            .insert(client_data)\
            .execute()
        return response.data[0]
    
    def update_client(self, client_id: int, client_data: Dict) -> Dict:
        """Update existing client"""
        response = self.supabase.table('clients')\
            .update(client_data)\
            .eq('id', client_id)\
            .eq('license_id', self.license_id)\
            .execute()
        return response.data[0]
    
    def delete_client(self, client_id: int) -> bool:
        """Delete client"""
        try:
            self.supabase.table('clients')\
                .delete()\
                .eq('id', client_id)\
                .eq('license_id', self.license_id)\
                .execute()
            return True
        except:
            return False
    
    # ==================== INVOICE OPERATIONS ====================
    
    def get_invoices(self, status: Optional[str] = None) -> List[Dict]:
        """Get all invoices for current license"""
        query = self.supabase.table('invoices')\
            .select('*, clients(name, email)')\
            .eq('license_id', self.license_id)
        
        if status:
            query = query.eq('status', status)
        
        response = query.order('invoice_date', desc=True).execute()
        return response.data or []
    
    def get_invoice(self, invoice_id: int, include_items: bool = True) -> Optional[Dict]:
        """Get invoice by ID with optional items"""
        if include_items:
            response = self.supabase.table('invoices')\
                .select('*, clients(*), invoice_items(*)')\
                .eq('id', invoice_id)\
                .eq('license_id', self.license_id)\
                .single()\
                .execute()
        else:
            response = self.supabase.table('invoices')\
                .select('*, clients(*)')\
                .eq('id', invoice_id)\
                .eq('license_id', self.license_id)\
                .single()\
                .execute()
        return response.data
    
    def create_invoice(self, invoice_data: Dict, items: List[Dict]) -> Dict:
        """Create new invoice with items"""
        invoice_data['license_id'] = self.license_id
        
        # Insert invoice
        response = self.supabase.table('invoices')\
            .insert(invoice_data)\
            .execute()
        invoice = response.data[0]
        
        # Insert items
        for item in items:
            item['invoice_id'] = invoice['id']
        
        self.supabase.table('invoice_items')\
            .insert(items)\
            .execute()
        
        return invoice
    
    def update_invoice(self, invoice_id: int, invoice_data: Dict, items: Optional[List[Dict]] = None) -> Dict:
        """Update invoice and optionally replace items"""
        # Update invoice
        response = self.supabase.table('invoices')\
            .update(invoice_data)\
            .eq('id', invoice_id)\
            .eq('license_id', self.license_id)\
            .execute()
        
        # Update items if provided
        if items is not None:
            # Delete old items
            self.supabase.table('invoice_items')\
                .delete()\
                .eq('invoice_id', invoice_id)\
                .execute()
            
            # Insert new items
            for item in items:
                item['invoice_id'] = invoice_id
            
            self.supabase.table('invoice_items')\
                .insert(items)\
                .execute()
        
        return response.data[0]
    
    def delete_invoice(self, invoice_id: int) -> bool:
        """Delete invoice (items deleted automatically via CASCADE)"""
        try:
            self.supabase.table('invoices')\
                .delete()\
                .eq('id', invoice_id)\
                .eq('license_id', self.license_id)\
                .execute()
            return True
        except:
            return False
    
    # ==================== SETTINGS OPERATIONS ====================
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get setting value"""
        try:
            response = self.supabase.table('app_settings')\
                .select('value')\
                .eq('license_id', self.license_id)\
                .eq('key', key)\
                .single()\
                .execute()
            return response.data['value'] if response.data else None
        except:
            return None
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set setting value (upsert)"""
        try:
            self.supabase.table('app_settings')\
                .upsert({
                    'license_id': self.license_id,
                    'key': key,
                    'value': value
                })\
                .execute()
            return True
        except:
            return False
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as dict"""
        response = self.supabase.table('app_settings')\
            .select('key, value')\
            .eq('license_id', self.license_id)\
            .execute()
        
        return {item['key']: item['value'] for item in (response.data or [])}
    
    def initialize_default_settings(self):
        """Initialize default settings for new license"""
        defaults = {
            'invoice_prefix': 'LAW',
            'invoice_year_format': 'YYYY',
            'invoice_padding': '4',
            'currency': 'INR',
            'default_tax_rate': '18',
            'auto_backup': 'false'
        }
        
        for key, value in defaults.items():
            self.set_setting(key, value)
    
    # ==================== ANALYTICS ====================
    
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        # Client count
        client_response = self.supabase.table('clients')\
            .select('*', count='exact')\
            .eq('license_id', self.license_id)\
            .execute()
        
        # Invoice stats
        invoice_response = self.supabase.table('invoices')\
            .select('total, status')\
            .eq('license_id', self.license_id)\
            .execute()
        
        invoices = invoice_response.data or []
        total_revenue = sum(float(inv['total'] or 0) for inv in invoices if inv['status'] == 'paid')
        pending_amount = sum(float(inv['total'] or 0) for inv in invoices if inv['status'] in ['draft', 'sent'])
        
        return {
            'client_count': client_response.count,
            'invoice_count': len(invoices),
            'total_revenue': total_revenue,
            'pending_amount': pending_amount,
            'paid_count': len([i for i in invoices if i['status'] == 'paid']),
            'draft_count': len([i for i in invoices if i['status'] == 'draft'])
        }


# Global instance
_supabase_service: Optional[SupabaseService] = None

def get_db() -> SupabaseService:
    """Get global Supabase service instance"""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service
