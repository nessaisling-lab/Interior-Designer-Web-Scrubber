"""Data model for interior designer information."""

from dataclasses import dataclass, field
from typing import Optional, Dict
import re


@dataclass
class Designer:
    """Represents an interior designer with contact information."""
    
    name: str
    source_url: str
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    social_media: Dict[str, str] = field(default_factory=dict)
    specialty: Optional[str] = None
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        if self.email:
            self.email = self._normalize_email(self.email)
        if self.phone:
            self.phone = self._normalize_phone(self.phone)
    
    @staticmethod
    def _normalize_email(email: str) -> Optional[str]:
        """Normalize and validate email address."""
        if not email:
            return None
        email = email.strip().lower()
        # Basic email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return email
        return None
    
    @staticmethod
    def _normalize_phone(phone: str) -> Optional[str]:
        """Normalize phone number format."""
        if not phone:
            return None
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        # Format as (XXX) XXX-XXXX if 10 digits
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            # US number with country code
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        return phone.strip()
    
    def to_dict(self) -> dict:
        """Convert Designer to dictionary for CSV export."""
        return {
            'name': self.name,
            'email': self.email or '',
            'phone': self.phone or '',
            'website': self.website or '',
            'address': self.address or '',
            'city': self.city or '',
            'state': self.state or '',
            'zip_code': self.zip_code or '',
            'social_media': ', '.join([f"{k}: {v}" for k, v in self.social_media.items()]) if self.social_media else '',
            'specialty': self.specialty or '',
            'source_url': self.source_url
        }
    
    def __hash__(self):
        """Hash based on name and website/email for deduplication."""
        identifier = self.website or self.email or self.name
        return hash((self.name.lower(), identifier.lower()))
    
    def __eq__(self, other):
        """Equality based on name and website/email."""
        if not isinstance(other, Designer):
            return False
        return (self.name.lower() == other.name.lower() and
                (self.website or self.email or '').lower() == 
                (other.website or other.email or '').lower())
