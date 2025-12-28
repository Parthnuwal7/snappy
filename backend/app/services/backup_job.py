"""Daily backup service for exporting user invoices to Supabase Storage"""
import os
import json
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from app.models.models import db, Invoice, InvoiceItem, Client


def get_supabase():
    """Get Supabase client"""
    try:
        from app.services.supabase_client import get_supabase_client
        return get_supabase_client()
    except (ValueError, ImportError):
        return None


def serialize_invoice(invoice: Invoice) -> Dict[str, Any]:
    """Serialize an invoice to a JSON-compatible dictionary"""
    return {
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'client_id': invoice.client_id,
        'client_name': invoice.client.name if invoice.client else None,
        'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
        'short_desc': invoice.short_desc,
        'subtotal': float(invoice.subtotal) if invoice.subtotal else 0,
        'tax_rate': float(invoice.tax_rate) if invoice.tax_rate else 0,
        'tax_amount': float(invoice.tax_amount) if invoice.tax_amount else 0,
        'total': float(invoice.total) if invoice.total else 0,
        'status': invoice.status,
        'paid_date': invoice.paid_date.isoformat() if invoice.paid_date else None,
        'notes': invoice.notes,
        'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
        'updated_at': invoice.updated_at.isoformat() if invoice.updated_at else None,
        'items': [
            {
                'id': item.id,
                'description': item.description,
                'quantity': float(item.quantity) if item.quantity else 0,
                'rate': float(item.rate) if item.rate else 0,
                'amount': float(item.amount) if item.amount else 0,
            }
            for item in invoice.items
        ] if invoice.items else []
    }


def create_backup_for_user(user_id: str, user_email: str = None) -> Optional[Dict[str, Any]]:
    """
    Create a JSON backup of all invoices for a specific user.
    
    Args:
        user_id: The Supabase user ID
        user_email: Optional user email for metadata
        
    Returns:
        Backup metadata dict or None if failed
    """
    supabase = get_supabase()
    if not supabase:
        print("❌ Supabase client not available for backup")
        return None
    
    try:
        # Get all invoices (for now, get all - multi-tenancy will filter by user)
        # TODO: Filter by user_id when multi-tenancy is fully implemented
        invoices = Invoice.query.all()
        
        if not invoices:
            print(f"ℹ️ No invoices to backup for user {user_id}")
            return None
        
        # Serialize all invoices
        backup_data = {
            'backup_type': 'full',
            'user_id': user_id,
            'user_email': user_email,
            'created_at': datetime.utcnow().isoformat(),
            'invoice_count': len(invoices),
            'invoices': [serialize_invoice(inv) for inv in invoices]
        }
        
        # Convert to JSON
        json_content = json.dumps(backup_data, indent=2, ensure_ascii=False)
        json_bytes = json_content.encode('utf-8')
        
        # Calculate checksum
        checksum = hashlib.sha256(json_bytes).hexdigest()
        
        # Generate file name
        today = date.today().isoformat()
        file_name = f"backup_{today}.json"
        file_path = f"{user_id}/{file_name}"
        
        # Upload to Supabase Storage
        bucket_name = 'invoice-backups'
        
        try:
            # Remove existing backup for today if any
            try:
                supabase.storage.from_(bucket_name).remove([file_path])
            except:
                pass
            
            # Upload new backup
            result = supabase.storage.from_(bucket_name).upload(
                file_path,
                json_bytes,
                file_options={
                    'content-type': 'application/json',
                    'upsert': 'true'
                }
            )
            
            print(f"✅ Backup created: {file_path} ({len(json_bytes)} bytes)")
            
            return {
                'user_id': user_id,
                'file_path': file_path,
                'file_name': file_name,
                'file_size_bytes': len(json_bytes),
                'invoice_count': len(invoices),
                'checksum_sha256': checksum,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Failed to upload backup: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Backup creation failed: {e}")
        return None


def get_user_backups(user_id: str) -> List[Dict[str, Any]]:
    """
    List all backups for a user.
    
    Args:
        user_id: The Supabase user ID
        
    Returns:
        List of backup file info
    """
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        bucket_name = 'invoice-backups'
        result = supabase.storage.from_(bucket_name).list(user_id)
        
        return [
            {
                'name': file.get('name'),
                'size': file.get('metadata', {}).get('size', 0),
                'created_at': file.get('created_at'),
                'path': f"{user_id}/{file.get('name')}"
            }
            for file in result
        ] if result else []
        
    except Exception as e:
        print(f"❌ Failed to list backups: {e}")
        return []


def download_backup(user_id: str, file_name: str) -> Optional[bytes]:
    """
    Download a backup file.
    
    Args:
        user_id: The Supabase user ID
        file_name: The backup file name
        
    Returns:
        File contents as bytes or None
    """
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        bucket_name = 'invoice-backups'
        file_path = f"{user_id}/{file_name}"
        
        result = supabase.storage.from_(bucket_name).download(file_path)
        return result
        
    except Exception as e:
        print(f"❌ Failed to download backup: {e}")
        return None


def delete_old_backups(user_id: str, retention_days: int = 30) -> int:
    """
    Delete backups older than retention_days.
    
    Args:
        user_id: The Supabase user ID
        retention_days: Number of days to keep backups
        
    Returns:
        Number of deleted backups
    """
    supabase = get_supabase()
    if not supabase:
        return 0
    
    try:
        from datetime import timedelta
        
        bucket_name = 'invoice-backups'
        backups = get_user_backups(user_id)
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        deleted_count = 0
        
        for backup in backups:
            created_at = backup.get('created_at')
            if created_at:
                try:
                    backup_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if backup_date < cutoff_date:
                        file_path = backup.get('path')
                        supabase.storage.from_(bucket_name).remove([file_path])
                        deleted_count += 1
                        print(f"🗑️ Deleted old backup: {file_path}")
                except:
                    pass
        
        return deleted_count
        
    except Exception as e:
        print(f"❌ Failed to delete old backups: {e}")
        return 0
