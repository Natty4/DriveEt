# payments/verification.py
import requests
import re
from decimal import Decimal
import logging
from dataclasses import dataclass
from typing import Optional
from django.conf import settings
from datetime import datetime
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

@dataclass
class VerifyResult:
    success: bool
    payer_name: Optional[str] = None
    payer_phone: Optional[str] = None
    payer_account: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_account: Optional[str] = None
    amount: Optional[Decimal] = None
    transaction_date: Optional[str] = None  # raw string from provider
    reference: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None

class PaymentVerifier:
    def __init__(self, mock_mode=settings.DEBUG):
        self.mock_mode = mock_mode

    def verify_payment(self, method: str, reference: str) -> VerifyResult:
        if self.mock_mode:
            return self._mock_verify(method, reference)

        method = method.upper()
        try:
            if method == 'TELEBIRR':
                return self._verify_telebirr(reference)
            elif method == 'BOA':
                return self._verify_boa(reference)
            elif method == 'DASHEN':
                return VerifyResult(success=False, error="Dashen verification not implemented (use screenshot)")
            else:
                return VerifyResult(success=False, error=f"Unsupported method: {method}")
        except Exception as e:
            logger.exception(f"Verification error for {method} {reference}")
            return VerifyResult(success=False, error=str(e))

    def _verify_telebirr(self, reference: str) -> VerifyResult:
        try:
            url = f"https://transactioninfo.ethiotelecom.et/receipt/{reference}"
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                return VerifyResult(success=False, error=f"HTTP {response.status_code}")

            html = response.text

            # Improved extractions
            payer_name = self._extract(html, r'የከፋይ ስም/Payer Name.*?</td>\s*<td[^>]*>\s*([^<]+)')
            payer_phone = self._extract(html, r'(?:የከፋይ ስልክ|Phone).*?</td>\s*<td[^>]*>\s*([^<]+)')
            receiver_name = self._extract(html, r'(?:የተቀባይ|Receiver|Business).*?</td>\s*<td[^>]*>\s*([^<]+)')
            receiver_account = self._extract(html, r'(?:የተቀባይ ስልክ|Receiver Phone|Account).*?</td>\s*<td[^>]*>\s*([^<]+)')
            amount_str = self._extract(html, r'የተከፈለው መጠን/Settled Amount.*?</td>\s*<td[^>]*>\s*([^<]+)')
            date_str = self._extract(html, r'(?:የክፍያ ቀን|Payment Date|Transaction Date).*?</td>\s*<td[^>]*>\s*([^<]+)')

            amount = None
            if amount_str:
                match = re.search(r'(\d[\d,]*\.?\d*)', amount_str.replace(',', ''))
                amount = Decimal(match.group(1)) if match else None

            if not payer_name or not amount:
                return VerifyResult(success=False, error="Incomplete transaction details")

            return VerifyResult(
                success=True,
                payer_name=payer_name.strip(),
                payer_phone=payer_phone.strip() if payer_phone else None,
                receiver_name=receiver_name.strip() if receiver_name else None,
                receiver_account=receiver_account.strip() if receiver_account else None,
                amount=amount,
                transaction_date=date_str.strip() if date_str else None,
                reference=reference
            )
        except requests.RequestException as e:
            return VerifyResult(success=False, error=f"Network error: {str(e)}")

    def _verify_boa(self, reference: str) -> VerifyResult:
        try:
            suffix = ""
            if '-' in reference:
                reference, suffix = reference.split('-', 1)
                suffix = f"-{suffix}"

            url = f"https://cs.bankofabyssinia.com/api/onlineSlip/getDetails/?id={reference}{suffix}"
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            })

            if response.status_code != 200:
                return VerifyResult(success=False, error=f"HTTP {response.status_code}")

            data = response.json()
            if data.get('header', {}).get('status') != 'success':
                return VerifyResult(success=False, error=data.get('header', {}).get('message', 'API error'))

            transaction = data.get('body', [{}])[0]

            amount_str = transaction.get('Transferred Amount', '')
            amount_match = re.search(r'[\d.]+', amount_str.replace(',', ''))
            amount = Decimal(amount_match.group(0)) if amount_match else None

            return VerifyResult(
                success=True,
                payer_name=transaction.get("Payer's Name"),
                payer_account=transaction.get('Source Account'),
                receiver_name=transaction.get('Beneficiary Name') or transaction.get('Destination Account Name'),
                receiver_account=transaction.get('Destination Account') or transaction.get('Beneficiary Account'),
                amount=amount,
                transaction_date=transaction.get('Transaction Date'),
                reference=transaction.get('Transaction Reference'),
                reason=transaction.get('Narrative')
            )
        except Exception as e:
            return VerifyResult(success=False, error=str(e))

    def _extract(self, html: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None

    def _mock_verify(self, method: str, reference: str) -> VerifyResult:
        # ... same as before but with more fields ...
        if reference.startswith('TEST'):
            return VerifyResult(
                success=True,
                payer_name="Test User",
                payer_phone="251911223344",
                payer_account="1234567890",
                receiver_name="DRIVEET",
                receiver_account=getattr(settings, f"{method}_RECEIVER_ACCOUNT", None),
                amount=Decimal('500.00'),
                transaction_date="2026-02-01 12:00:00",
                reference=reference
            )
        return VerifyResult(success=False, error="Mock payment not found")